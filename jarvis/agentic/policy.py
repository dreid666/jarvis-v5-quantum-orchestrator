"""Policy decisions and explicit approval state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalState(str, Enum):
    ALLOWED = "allowed"
    PENDING = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class PolicyDecision:
    risk: str
    state: ApprovalState
    requires_approval: bool = False


class ActionPolicy:
    """Deny-by-default policy for agentic actions."""

    HIGH_RISK_TOOLS = {"shell", "subprocess", "bash", "cmd", "powershell", "curl", "wget", "delete_file"}
    MEDIUM_RISK_TOOLS = {"network", "http", "web_request", "api_call", "write_file", "rename_file", "synthesize"}
    HIGH_RISK_ACTIONS = {"read_secret", "write_secret", "export_env"}
    LOW_RISK_TOOLS = {"memory_lookup", "guardrail_check", "search"}

    def evaluate(self, action: Mapping[str, Any] | Any) -> PolicyDecision:
        if isinstance(action, Mapping):
            tool = str(action.get("tool", "")).casefold()
            name = str(action.get("name", "")).casefold()
        else:
            tool = str(getattr(action, "tool", "")).casefold()
            name = str(getattr(action, "name", "")).casefold()

        if tool in self.HIGH_RISK_TOOLS or name in self.HIGH_RISK_ACTIONS:
            return PolicyDecision(RiskLevel.HIGH.value, ApprovalState.PENDING, requires_approval=True)
        if tool in self.MEDIUM_RISK_TOOLS:
            return PolicyDecision(RiskLevel.MEDIUM.value, ApprovalState.PENDING, requires_approval=True)
        if tool in self.LOW_RISK_TOOLS:
            return PolicyDecision(RiskLevel.LOW.value, ApprovalState.ALLOWED, requires_approval=False)
        return PolicyDecision(RiskLevel.HIGH.value, ApprovalState.PENDING, requires_approval=True)

    def approve(self, action: Mapping[str, Any] | Any) -> ApprovalState:
        decision = self.evaluate(action)
        if decision.state == ApprovalState.PENDING:
            return ApprovalState.APPROVED
        return decision.state

    def deny(self, action: Mapping[str, Any] | Any) -> ApprovalState:
        return ApprovalState.DENIED
