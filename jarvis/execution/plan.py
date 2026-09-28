"""Execution and planning for safe evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jarvis.execution.safe_python import SafePythonEvaluator


@dataclass
class PlannedAction:
    name: str
    tool: str
    arguments: dict[str, Any]
    risk: str = "low"
    requires_approval: bool = False

    def __init__(self, name: str, tool: str, arguments: dict[str, Any], risk: str = "low", requires_approval: bool = False):
        self.name = name
        self.tool = tool
        self.arguments = arguments
        self.risk = risk
        self.requires_approval = requires_approval

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tool": self.tool,
            "arguments": dict(self.arguments),
            "risk": self.risk,
            "requires_approval": self.requires_approval,
        }


@dataclass
class ExecutionPlan:
    goal: str
    domain: str
    actions: tuple[PlannedAction, ...] = field(default_factory=tuple)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "domain": self.domain,
            "actions": [action.to_dict() for action in self.actions],
            "rationale": self.rationale,
        }
