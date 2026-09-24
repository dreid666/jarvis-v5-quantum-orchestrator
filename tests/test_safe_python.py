"""Tests for the safe evaluator."""

import pytest

from jarvis.execution.plan import SafePythonEvaluator as PlanSafePythonEvaluator
from jarvis.execution.safe_python import SafePythonEvaluator


def test_safe_python_evaluates_arithmetic():
    assert SafePythonEvaluator().evaluate("(2 + 3) * 7") == 35


def test_safe_python_allows_allowlisted_builtins():
    assert SafePythonEvaluator().evaluate("len([1, 2, 3])") == 3


def test_safe_python_rejects_imports():
    with pytest.raises(ValueError):
        SafePythonEvaluator().evaluate("__import__('os').system('id')")


def test_safe_python_accepts_assignment_statement():
    env = SafePythonEvaluator().evaluate_statement("result = 42 + 8")
    assert env["result"] == 50


def test_execution_plan_re_exports_canonical_evaluator():
    assert PlanSafePythonEvaluator is SafePythonEvaluator
