"""Validation rules for parsed PSYKER documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .errors import ReferenceError, SourceSpan
from .model import AgentDef, AgentDocument, TaskDocument, WorkerDocument


@dataclass
class ValidationContext:
    workers: Dict[str, object]
    agents: Dict[str, object]
    tasks: Dict[str, object]


def validate_agent(agent: AgentDef, context: ValidationContext) -> None:
    for use in agent.uses:
        if use.worker_name not in context.workers:
            raise ReferenceError(
                f"Agent '{agent.name}' references unknown worker '{use.worker_name}'",
                SourceSpan(agent.source_path, use.line, use.column),
                hint="Load the worker definition before loading this agent.",
            )
        if use.count <= 0:
            raise ReferenceError(
                f"Agent '{agent.name}' has invalid worker count {use.count}",
                SourceSpan(agent.source_path, use.line, use.column),
                hint="Use a worker count greater than zero.",
            )


def validate_document(document: object, context: ValidationContext) -> None:
    if isinstance(document, WorkerDocument):
        return
    if isinstance(document, TaskDocument):
        return
    if isinstance(document, AgentDocument):
        validate_agent(document.agent, context)
        return
    raise TypeError(f"Unknown document type: {type(document)!r}")

