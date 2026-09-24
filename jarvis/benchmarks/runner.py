"""Deterministic benchmark runner for agentic runtime checks."""

from __future__ import annotations

import statistics
import time
from typing import Any

from jarvis.agentic.wingman import WingmanAgent
from jarvis.execution.safe_python import SafePythonEvaluator


def benchmark_agentic_runtime(iterations: int = 5) -> dict[str, Any]:
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    guardrail_samples: list[float] = []
    planner_samples: list[float] = []
    evaluator_samples: list[float] = []
    full_samples: list[float] = []

    evaluator = SafePythonEvaluator()
    agent = WingmanAgent()

    for _ in range(iterations):
        start = time.perf_counter()
        agent.guardrail.screen("Design a secure quantum workflow with safe, deterministic evaluation.")
        guardrail_samples.append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        agent.plan("Design and validate a secure quantum workflow")
        planner_samples.append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        evaluator.evaluate("(2 + 3) * 7")
        evaluator_samples.append((time.perf_counter() - start) * 1000)

        start = time.perf_counter()
        result = agent.execute("Design and validate a secure quantum workflow", approve=True)
        full_samples.append((time.perf_counter() - start) * 1000)
        if not result["approved"]:
            raise RuntimeError("unexpected approval failure in benchmark")

    return {
        "iterations": iterations,
        "guardrail_ms": {
            "mean": round(statistics.mean(guardrail_samples), 3),
            "p95": round(sorted(guardrail_samples)[max(0, int(0.95 * len(guardrail_samples)) - 1)], 3),
        },
        "planner_ms": {
            "mean": round(statistics.mean(planner_samples), 3),
            "p95": round(sorted(planner_samples)[max(0, int(0.95 * len(planner_samples)) - 1)], 3),
        },
        "evaluator_ms": {
            "mean": round(statistics.mean(evaluator_samples), 3),
            "p95": round(sorted(evaluator_samples)[max(0, int(0.95 * len(evaluator_samples)) - 1)], 3),
        },
        "full_pipeline_ms": {
            "mean": round(statistics.mean(full_samples), 3),
            "p95": round(sorted(full_samples)[max(0, int(0.95 * len(full_samples)) - 1)], 3),
        },
    }
