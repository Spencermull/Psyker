"""Runtime registry, load pipeline, and execution state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from .model import AgentDef, AgentDocument, TaskDef, TaskDocument, WorkerDef, WorkerDocument
from .parser import parse_path
from .validator import ValidationContext, validate_document


@dataclass
class RuntimeState:
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

