import inspect

import pytest

from jarvis.agentic.research_workflow import ResearchWorkflowAgent
from jarvis.execution.safe_python import SafePythonEvaluator


class FakeRetrievalBackend:
    def search(self, query: str):
        return [
            {
                "title": "Local note",
                "snippet": f"evidence for {query}",
                "citation": "note-1",
                "uri": "memory://note-1",
            }
        ]


class FakeSandbox:
    def __init__(self, available: bool = True):
        self._available = available

    def available(self) -> bool:
        return self._available

    def execute(self, code: str):
        return {"status": "ok", "result": code.count("=")}


def test_safe_python_evaluator_rejects_unsafe_ast_nodes():
    evaluator = SafePythonEvaluator()
    assert evaluator.evaluate("(2 + 3) * 7") == 35
    with pytest.raises(ValueError):
        evaluator.evaluate("__import__('os').system('id')")
    with pytest.raises(ValueError):
        evaluator.evaluate("os.path.join('a', 'b')")
    with pytest.raises(ValueError):
        evaluator.evaluate("int('7')")
    with pytest.raises(ValueError):
        evaluator.evaluate("pow(2, x=3)")


def test_research_workflow_reports_unavailable_retrieval_without_fabrication():
    agent = ResearchWorkflowAgent()
    result = agent.retrieve_literature("quantum transformers")
    assert result["status"] == "unavailable"
    assert result["results"] == []
    assert "Grounded references" not in result["message"]


def test_research_workflow_requires_authorization_and_approval_for_external_tools():
    agent = ResearchWorkflowAgent()
    backend = FakeRetrievalBackend()

    rejected = agent.execute_tool("not_registered")
    assert rejected["status"] == "rejected"

    disabled = agent.retrieve_literature("quantum transformers", backend=backend, approve=True, allow_external=False)
    assert disabled["status"] == "disabled"

    pending = agent.retrieve_literature("quantum transformers", backend=backend, allow_external=True, approve=False)
    assert pending["status"] == "pending_approval"

    approved = agent.retrieve_literature("quantum transformers", backend=backend, allow_external=True, approve=True)
    assert approved["status"] == "ok"
    assert approved["results"][0]["citation"] == "note-1"
    assert approved["results"][0]["uri"] == "memory://note-1"


def test_research_workflow_uses_controlled_sandbox_interface():
    agent = ResearchWorkflowAgent()

    unavailable = agent.execute_code("result = 2 + 2")
    assert unavailable["status"] == "unavailable"

    disabled = agent.execute_code("result = 2 + 2", sandbox=FakeSandbox(), approve=True, allow_external=False)
    assert disabled["status"] == "disabled"

    pending = agent.execute_code("result = 2 + 2", sandbox=FakeSandbox(), allow_external=True, approve=False)
    assert pending["status"] == "pending_approval"

    approved = agent.execute_code("result = 2 + 2", sandbox=FakeSandbox(), allow_external=True, approve=True)
    assert approved["status"] == "ok"
    assert approved["result"] == 1


def test_research_workflow_assertions_and_retry_results_are_preserved():
    agent = ResearchWorkflowAgent()
    assert agent.verify_assertion("120 + 165", 285)["matched"] is True

    with pytest.raises(ValueError):
        agent.verify_assertion("__import__('os').system('id')", 0)
    with pytest.raises(ValueError):
        agent.verify_assertion("sum([1, 2, 3])", 6)
    with pytest.raises(ValueError):
        agent.verify_assertion("pow(2, y=3)", 8)

    attempts = {"count": 0}

    def flaky_tool():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")
        return {"status": "ok", "value": "recovered"}

    agent.register_tool("flaky", flaky_tool)
    recovered = agent.execute_tool("flaky", retries=1, approve=True)
    assert recovered["status"] == "ok"
    assert recovered["attempts"] == 2
    assert recovered["value"] == "recovered"

    def always_fail():
        raise RuntimeError("still broken")

    agent.register_tool("always_fail", always_fail)
    failed = agent.execute_tool("always_fail", retries=1, approve=True)
    assert failed["status"] == "error"
    assert failed["attempts"] == 2
    assert failed["message"] == "still broken"


def test_research_workflow_run_signature_and_shape():
    signature = inspect.signature(ResearchWorkflowAgent.run)
    assert signature.parameters["goal"].default is inspect._empty
    assert signature.parameters["approve"].default is False
    assert signature.parameters["allow_external"].default is False

    result = ResearchWorkflowAgent().run(
        "evaluate a local hypothesis",
        arithmetic_assertion="3 * 5",
        expected_value=15,
    )
    assert result["status"] == "ok"
    assert result["assertion"]["matched"] is True
    assert result["hypotheses"][0]["kind"] == "hypothesis"


def test_research_workflow_run_propagates_pending_approval():
    result = ResearchWorkflowAgent().run(
        "evaluate a hypothesis with external evidence",
        retrieval_backend=FakeRetrievalBackend(),
        allow_external=True,
        approve=False,
    )
    assert result["status"] == "pending_approval"
    assert result["retrieval"]["status"] == "pending_approval"


def test_research_workflow_run_returns_structured_assertion_error():
    result = ResearchWorkflowAgent().run(
        "evaluate a local hypothesis",
        arithmetic_assertion="__import__('os').system('id')",
        expected_value=0,
    )
    assert result["status"] == "error"
    assert result["assertion"]["status"] == "error"
    assert result["assertion"]["matched"] is False
