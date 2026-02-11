"""Runtime registry, load pipeline, and execution state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Dict

from .errors import AccessError, ExecError, PermissionError, ReferenceError
from .model import AgentDef, AgentDocument, TaskDef, TaskDocument, WorkerDef, WorkerDocument
from .parser import parse_path
from .sandbox import Sandbox
from .validator import ValidationContext, validate_document


@dataclass(frozen=True)
class ExecutionResult:
    status_code: int
    stdout: str
    stderr: str
    worker: str
    agent: str
    task: str


@dataclass
class RuntimeState:
    sandbox: Sandbox = field(default_factory=Sandbox.create_default)
    workers: Dict[str, WorkerDef] = field(default_factory=dict)
    agents: Dict[str, AgentDef] = field(default_factory=dict)
    tasks: Dict[str, TaskDef] = field(default_factory=dict)
    _rr_index: Dict[str, int] = field(default_factory=dict)

    def load_file(self, path: Path) -> object:
        document = parse_path(path)

        workers_copy = dict(self.workers)
        agents_copy = dict(self.agents)
        tasks_copy = dict(self.tasks)
        context = ValidationContext(workers=workers_copy, agents=agents_copy, tasks=tasks_copy)
        validate_document(document, context)

        if isinstance(document, WorkerDocument):
            workers_copy[document.worker.name] = document.worker
        elif isinstance(document, AgentDocument):
            agents_copy[document.agent.name] = document.agent
        elif isinstance(document, TaskDocument):
            for task in document.tasks:
                tasks_copy[task.name] = task
        else:
            raise TypeError(f"Unknown document type: {type(document)!r}")

        self.workers = workers_copy
        self.agents = agents_copy
        self.tasks = tasks_copy
        return document

    def run_task(self, agent_name: str, task_name: str) -> ExecutionResult:
        agent = self.agents.get(agent_name)
        if agent is None:
            raise ReferenceError(f"Unknown agent '{agent_name}'", hint="Load agent files before running.")
        task = self.tasks.get(task_name)
        if task is None:
            raise ReferenceError(f"Unknown task '{task_name}'", hint="Load task files before running.")

        worker = self._select_worker(agent_name, agent)
        self._enforce_access(task, agent_name, worker.name)

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        for stmt in task.statements:
            self._enforce_capability(worker, stmt.op)
            out, err = self._run_statement(agent_name, worker, stmt.op, stmt.arg)
            if out:
                stdout_parts.append(out)
            if err:
                stderr_parts.append(err)

        return ExecutionResult(
            status_code=0,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            worker=worker.name,
            agent=agent_name,
            task=task_name,
        )

    def _select_worker(self, agent_name: str, agent: AgentDef) -> WorkerDef:
        pool: list[str] = []
        for use in agent.uses:
            pool.extend([use.worker_name] * use.count)
        if not pool:
            raise ReferenceError(f"Agent '{agent_name}' has no workers configured.")

        index = self._rr_index.get(agent_name, 0)
        selected_name = pool[index % len(pool)]
        self._rr_index[agent_name] = (index + 1) % len(pool)
        worker = self.workers.get(selected_name)
        if worker is None:
            raise ReferenceError(
                f"Worker '{selected_name}' referenced by agent '{agent_name}' is not loaded",
                hint="Load referenced workers before loading/running agent tasks.",
            )
        return worker

    def _enforce_access(self, task: TaskDef, agent_name: str, worker_name: str) -> None:
        if task.access is None:
            raise AccessError(
                f"Task '{task.name}' has no @access block and defaults to deny-all",
                hint="Add @access { agents: [...], workers: [...] } to allow execution.",
            )
        if task.access.agents and agent_name not in task.access.agents:
            raise AccessError(
                f"Agent '{agent_name}' is not allowed to run task '{task.name}'",
                hint="Include the agent in @access.agents.",
            )
        if task.access.workers and worker_name not in task.access.workers:
            raise AccessError(
                f"Worker '{worker_name}' is not allowed to execute task '{task.name}'",
                hint="Include the worker in @access.workers.",
            )

    def _enforce_capability(self, worker: WorkerDef, op: str) -> None:
        allowed = {entry.capability for entry in worker.allows}
        if op not in allowed:
            raise PermissionError(
                f"Worker '{worker.name}' lacks required capability '{op}'",
                hint="Add an allow statement in the worker definition.",
            )

    def _run_statement(self, agent_name: str, worker: WorkerDef, op: str, arg: str) -> tuple[str, str]:
        value = _dequote(arg)
        if op == "fs.open":
            target = self.sandbox.resolve_under_root(value)
            if not target.exists() or not target.is_file():
                self.sandbox.log(agent_name, worker.name, op, "error")
                raise ExecError(f"File not found for fs.open: {target}")
            content = target.read_text(encoding="utf-8")
            self.sandbox.log(agent_name, worker.name, op, "ok")
            return content, ""

        if op == "fs.create":
            target = self.sandbox.resolve_under_root(value)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix:
                target.touch(exist_ok=True)
            else:
                target.mkdir(parents=True, exist_ok=True)
            self.sandbox.log(agent_name, worker.name, op, "ok")
            return "", ""

        if op == "exec.ps":
            return self._run_process(agent_name, worker, op, ["powershell", "-NoProfile", "-Command", value])
        if op == "exec.cmd":
            return self._run_process(agent_name, worker, op, ["cmd", "/c", value])

        raise ExecError(f"Unsupported operation '{op}'")

    def _run_process(self, agent_name: str, worker: WorkerDef, op: str, command: list[str]) -> tuple[str, str]:
        cwd = self.sandbox.workspace
        if worker.cwd:
            cwd = self.sandbox.resolve_under_root(_dequote(worker.cwd))
        cwd.mkdir(parents=True, exist_ok=True)

        try:
            proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        except OSError as exc:
            self.sandbox.log(agent_name, worker.name, op, "error")
            raise ExecError(f"Failed to execute '{command[0]}': {exc}") from exc

        if proc.returncode != 0:
            self.sandbox.log(agent_name, worker.name, op, "error")
            raise ExecError(
                f"{op} failed with exit code {proc.returncode}",
                hint=f"stdout={proc.stdout.strip()} stderr={proc.stderr.strip()}",
            )

        self.sandbox.log(agent_name, worker.name, op, "ok")
        return proc.stdout, proc.stderr


def _dequote(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"')
    return value
