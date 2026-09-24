"""Focused regressions for PR review fixes."""

from __future__ import annotations

import json

from jarvis.benchmarks.runner import _p95
from jarvis.config.loader import ModuleLoader
from jarvis.config.settings import Settings
from jarvis.core.workflow import Workflow, WorkflowNode
from jarvis.memory.vector_store import VectorMemoryStore
from jarvis.observability.logging import AuditEvent, StructuredLogger, get_logger
from jarvis.security.audit import AuditLog


def test_workflow_detects_cycles():
    workflow = Workflow(
        name="cycle",
        nodes=[
            WorkflowNode("a", "search", dependencies=["b"]),
            WorkflowNode("b", "search", dependencies=["a"]),
        ],
    )

    try:
        workflow.topological_order()
        assert False, "expected cycle detection"
    except ValueError as exc:
        assert "cycle detected" in str(exc)


def test_audit_log_redacts_hyphenated_api_keys():
    audit = AuditLog()
    audit.record("deploy", "ok", {"api-key": "secret", "note": "kept"})
    assert audit.entries[0]["details"] == {"note": "kept"}


def test_structured_logger_stores_sanitized_audit_copies():
    logger = StructuredLogger("audit-copy")
    event = AuditEvent("deploy", details={"api-key": "secret"})
    logger.log_audit(event)
    event.details["later"] = "mutation"

    trail = logger.get_audit_trail()
    assert trail[0]["details"] == {}


def test_structured_logger_emits_valid_json(capsys):
    logger = StructuredLogger("json-log")
    logger.info("hello", scope="test")
    payload = capsys.readouterr().err.strip().splitlines()[-1]
    assert json.loads(payload)["message"] == "hello"


def test_get_logger_caches_by_name():
    assert get_logger("alpha") is get_logger("alpha")
    assert get_logger("alpha") is not get_logger("beta")


def test_vector_memory_store_defaults_to_lazy_lexical_mode():
    store = VectorMemoryStore()
    assert store._model is None
    assert store._model_attempted is False
    store.add_memory("doc-1", "quantum workflow", {})
    assert store.search("quantum")[0]["id"] == "doc-1"


def test_module_loader_restores_default_module_exports():
    loader = ModuleLoader(Settings(enabled_modules=["vqc", "aletheia", "qnlp"]))
    modules = loader.load_enabled()
    assert sorted(modules) == ["aletheia", "qnlp", "vqc"]
    assert loader.failed == {}


def test_benchmark_p95_uses_upper_nearest_rank():
    assert _p95([1.0, 2.0, 3.0, 4.0, 5.0]) == 5.0
