"""Deterministic benchmark runner for agentic runtime checks."""

import pytest

from jarvis.benchmarks.runner import benchmark_agentic_runtime
from jarvis.execution.safe_python import SafePythonEvaluator


def test_benchmark_agentic_runtime_completes():
    result = benchmark_agentic_runtime(1)
    assert result["iterations"] == 1
    assert result["full_pipeline_ms"]["mean"] >= 0


def test_safe_python_rejects_large_exponent():
    with pytest.raises(ValueError, match="power exponent too large"):
        SafePythonEvaluator().evaluate("10 ** 10**9")


def test_safe_python_rejects_large_list_repetition():
    with pytest.raises(ValueError, match="collection result too large"):
        SafePythonEvaluator().evaluate("[0] * 10001")
