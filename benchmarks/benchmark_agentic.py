"""Tests for the safe evaluator."""

from jarvis.benchmarks import SafePythonEvaluator


def test_safe_python_evaluates_arithmetic():
    evaluator = SafePythonEvaluator()
    assert evaluator.evaluate("(2 + 3) * 7") == 35


def test_safe_python_rejects_imports():
    evaluator = SafePythonEvaluator()
    try:
        evaluator.evaluate("__import__('os').system('id')")
        assert False, "expected rejection of import-like access"
    except ValueError:
        pass


def test_safe_python_accepts_assignment_statement():
    evaluator = SafePythonEvaluator()
    env = evaluator.evaluate_statement("result = 42 + 8")
    assert env["result"] == 50
