"""Tests for the approval-aware research orchestrator remediation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from jarvis.agentic.research_orchestrator import (
    NullRetrievalProvider,
    PlannedToolCall,
    ResearchOrchestrator,
    RestrictedExpressionEvaluator,
    SandboxRunResult,
)


class SequenceSandboxRunner:
    def __init__(self, results: list[SandboxRunResult]) -> None:
        self._results = results
        self.calls: list[str] = []

    def run(self, code: str) -> SandboxRunResult:
        self.calls.append(code)
        return self._results.pop(0)


def test_research_orchestrator_module_contains_no_exec_or_eval_calls():
    path = Path(__file__).resolve().parents[1] / "jarvis" / "agentic" / "research_orchestrator.py"
    tree = ast.parse(path.read_text())
    banned = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}
    }
    assert banned == set()


def test_blocked_sandbox_execution_when_backend_unavailable():
    orchestrator = ResearchOrchestrator(trusted_mode=True, approved_actions=frozenset({"execute_python"}))
    result = orchestrator.execute_plan(
        (
            PlannedToolCall("sandbox", "execute_python", {"code": "result = 2 + 2"}),
        )
    )

    assert result.success is False
    assert result.requires_replan is True
    assert result.trace[0].status == "unavailable"
    assert "Sandbox backend unavailable" in result.trace[0].summary


def test_restricted_evaluator_accepts_allowed_math_and_rejects_dangerous_constructs():
    evaluator = RestrictedExpressionEvaluator()
    assert evaluator.evaluate("sum([1, 2, 3]) + sqrt(16)") == 10

    with pytest.raises(ValueError, match="invalid syntax"):
        evaluator.evaluate("sum([1, 2]")

    with pytest.raises(ValueError, match="function not allowed|attribute access is not allowed|name not allowed"):
        evaluator.evaluate("__import__('os').system('id')")


def test_high_risk_tool_calls_require_trusted_mode_and_approval():
    plan = (PlannedToolCall("sandbox", "execute_python", {"code": "result = 2 + 2"}),)

    untrusted = ResearchOrchestrator(approved_actions=frozenset({"execute_python"}))
    untrusted_result = untrusted.execute_plan(plan)
    assert untrusted_result.trace[0].status == "denied"
    assert "trusted mode" in untrusted_result.trace[0].summary

    missing_approval = ResearchOrchestrator(trusted_mode=True)
    missing_approval_result = missing_approval.execute_plan(plan)
    assert missing_approval_result.trace[0].status == "denied"
    assert "explicit approval" in missing_approval_result.trace[0].summary


def test_retrieval_unavailable_does_not_invent_citations():
    provider = NullRetrievalProvider()
    result = provider.search("quantum transformers")

    assert result.available is False
    assert result.documents == ()
    assert "unavailable" in result.message.lower()
    assert "citation" not in result.message.lower()


def test_symbolic_verification_uses_tolerance_for_numeric_results():
    orchestrator = ResearchOrchestrator()
    result = orchestrator.tools.execute(
        PlannedToolCall("verify", "verify_symbolic", {"expression": "sqrt(2) * sqrt(2)", "expected": 2.0}),
        trusted_mode=False,
        approved_actions=frozenset(),
    )

    assert result.status == "success"
    assert result.payload["matches_expected"] is True

    nan_result = orchestrator.tools.execute(
        PlannedToolCall("verify", "verify_symbolic", {"expression": "sqrt(4)", "expected": float("nan")}),
        trusted_mode=False,
        approved_actions=frozenset(),
    )
    assert nan_result.payload["matches_expected"] is False


def test_retry_success_allows_execution_to_complete():
    runner = SequenceSandboxRunner(
        [
            SandboxRunResult(True, False, "first attempt failed", stderr="boom"),
            SandboxRunResult(True, True, "retry attempt succeeded", output=4),
        ]
    )
    orchestrator = ResearchOrchestrator(
        sandbox_runner=runner,
        trusted_mode=True,
        approved_actions=frozenset({"execute_python"}),
    )

    result = orchestrator.execute_plan(
        (
            PlannedToolCall(
                "sandbox",
                "execute_python",
                {"code": "result = 1 / 0"},
                retry_arguments={"code": "result = 2 + 2"},
            ),
        )
    )

    assert result.success is True
    assert result.requires_replan is False
    assert [entry.status for entry in result.trace] == ["failed", "retry_succeeded"]
    assert runner.calls == ["result = 1 / 0", "result = 2 + 2"]


def test_retry_failures_are_retained_and_reported():
    runner = SequenceSandboxRunner(
        [
            SandboxRunResult(True, False, "first attempt failed", stderr="boom"),
            SandboxRunResult(True, False, "retry attempt failed", stderr="still boom"),
        ]
    )
    orchestrator = ResearchOrchestrator(
        sandbox_runner=runner,
        trusted_mode=True,
        approved_actions=frozenset({"execute_python"}),
    )

    result = orchestrator.execute_plan(
        (
            PlannedToolCall(
                "sandbox",
                "execute_python",
                {"code": "result = 1 / 0"},
                retry_arguments={"code": "result = 1 / 0"},
            ),
        )
    )

    assert result.success is False
    assert result.requires_replan is True
    assert [entry.status for entry in result.trace] == ["failed", "retry_failed"]
    assert runner.calls == ["result = 1 / 0", "result = 1 / 0"]
    assert "step sandbox" in result.summary.lower()
    assert "retry attempt failed" in result.summary.lower()

