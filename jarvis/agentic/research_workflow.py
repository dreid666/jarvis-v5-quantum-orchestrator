"""Safe, approval-aware research workflow utilities."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from jarvis.agentic.policy import ActionPolicy, ApprovalState
from jarvis.execution.plan import ExecutionPlan, PlannedAction
from jarvis.security.audit import AuditLog
from jarvis.security.guardrails import PromptGuardrail


class IsolatedSandbox(Protocol):
    """Controlled execution interface for explicitly approved code execution."""

    def available(self) -> bool:
        ...

    def execute(self, code: str) -> Mapping[str, Any]:
        ...


class RetrievalBackend(Protocol):
    """Explicit retrieval interface used only when supplied by the caller."""

    def search(self, query: str) -> list[Mapping[str, Any]]:
        ...


@dataclass(frozen=True)
class ToolSpec:
    name: str
    func: Callable[..., Any]
    tool: str = "function"
    description: str = ""
    external: bool = False


class SafeArithmeticEvaluator:
    """Evaluate a narrow arithmetic subset without using exec/eval."""

    SAFE_FUNCS = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        "pow": pow,
    }

    def evaluate(self, expression: str, context: Mapping[str, Any] | None = None) -> Any:
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("expression must be a non-empty string")
        tree = ast.parse(expression, mode="eval")
        return self._eval_node(tree.body, dict(context or {}))

    def _eval_node(self, node: ast.AST, context: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, bool):
                raise ValueError("unsupported constant type")
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in context:
                raise ValueError(f"name not allowed: {node.id}")
            value = context[node.id]
            if type(value) not in (int, float, bool):
                raise ValueError(f"unsupported value for name: {node.id}")
            return value
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            if type(node.op) is ast.Add:
                return left + right
            if type(node.op) is ast.Sub:
                return left - right
            if type(node.op) is ast.Mult:
                return left * right
            if type(node.op) is ast.Div:
                return left / right
            if type(node.op) is ast.FloorDiv:
                return left // right
            if type(node.op) is ast.Mod:
                return left % right
            if type(node.op) is ast.Pow:
                return left ** right
            raise ValueError("operator not allowed")
        if isinstance(node, ast.UnaryOp):
            value = self._eval_node(node.operand, context)
            if type(node.op) is ast.UAdd:
                return +value
            if type(node.op) is ast.USub:
                return -value
            raise ValueError("unary operator not allowed")
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                if type(op) is ast.Eq:
                    result = result and (left == right)
                elif type(op) is ast.NotEq:
                    result = result and (left != right)
                elif type(op) is ast.Lt:
                    result = result and (left < right)
                elif type(op) is ast.LtE:
                    result = result and (left <= right)
                elif type(op) is ast.Gt:
                    result = result and (left > right)
                elif type(op) is ast.GtE:
                    result = result and (left >= right)
                else:
                    raise ValueError("comparison operator not allowed")
                left = right
            return result
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only direct function calls are allowed")
            if node.func.id not in self.SAFE_FUNCS:
                raise ValueError(f"function not allowed: {node.func.id}")
            args = [self._eval_node(arg, context) for arg in node.args]
            return self.SAFE_FUNCS[node.func.id](*args)
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item, context) for item in node.elts)
        if isinstance(node, ast.List):
            return [self._eval_node(item, context) for item in node.elts]
        raise ValueError(f"syntax not allowed: {type(node).__name__}")


class ResearchWorkflowAgent:
    """Small, deterministic research workflow with explicit approval gates."""

    def __init__(
        self,
        *,
        guardrail: PromptGuardrail | None = None,
        policy: ActionPolicy | None = None,
        audit: AuditLog | None = None,
        evaluator: SafeArithmeticEvaluator | None = None,
    ) -> None:
        self.guardrail = guardrail or PromptGuardrail()
        self.policy = policy or ActionPolicy()
        self.audit = audit or AuditLog()
        self.evaluator = evaluator or SafeArithmeticEvaluator()
        self._tools: dict[str, ToolSpec] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.register_tool("memory_lookup", self._memory_lookup, description="Return deterministic local context")
        self.register_tool("retrieve_literature", self._retrieve_literature, tool="api_call", description="Use a supplied retrieval backend", external=True)
        self.register_tool("execute_python", self._execute_python, tool="subprocess", description="Run code in an isolated sandbox", external=True)
        self.register_tool("safe_assert", self._safe_assert, description="Verify arithmetic assertions safely")
        self.register_tool("summarize", self._summarize, description="Summarize hypotheses, evidence, and uncertainty")

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        tool: str = "function",
        description: str = "",
        external: bool = False,
    ) -> None:
        if not name:
            raise ValueError("tool name is required")
        self._tools[name] = ToolSpec(name=name, func=func, tool=tool, description=description, external=external)

    def plan(self, goal: str, *, request_retrieval: bool = False, request_execution: bool = False) -> ExecutionPlan:
        normalized = goal.strip() if isinstance(goal, str) else ""
        if not normalized:
            raise ValueError("goal is required")
        actions = [
            PlannedAction("screen_goal", "guardrail_check", {"goal": normalized}, "low"),
            PlannedAction("read_context", "memory_lookup", {"query": normalized}, "low"),
        ]
        if request_retrieval:
            actions.append(PlannedAction("retrieve_evidence", "api_call", {"query": normalized}, "medium", True))
        if request_execution:
            actions.append(PlannedAction("run_isolated_code", "subprocess", {"goal": normalized}, "high", True))
        actions.append(PlannedAction("summarize_findings", "function", {"goal": normalized}, "low"))
        return ExecutionPlan(
            goal=normalized,
            domain="research_orchestration",
            actions=tuple(actions),
            rationale="Separate hypotheses from evidence and gate external side effects behind approval.",
        )

    def execute_tool(
        self,
        name: str,
        *,
        approve: bool = False,
        allow_external: bool = False,
        retries: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if name not in self._tools:
            self.audit.record(name, "rejected", {"reason": "tool not authorized"})
            return {"status": "rejected", "message": f"tool not authorized: {name}"}

        spec = self._tools[name]
        decision = self.policy.evaluate({"name": spec.name, "tool": spec.tool})
        state = decision.state

        if spec.external and not allow_external:
            self.audit.record(name, "disabled", {"reason": "external execution disabled", "risk": decision.risk})
            return {"status": "disabled", "message": "external execution disabled", "risk": decision.risk}

        if state == ApprovalState.PENDING and not approve:
            self.audit.record(name, state.value, {"risk": decision.risk})
            return {"status": state.value, "message": "explicit approval required", "risk": decision.risk}

        if state == ApprovalState.PENDING and approve:
            state = self.policy.approve({"name": spec.name, "tool": spec.tool})

        last_result: dict[str, Any] | None = None
        total_attempts = max(0, retries) + 1
        for attempt in range(1, total_attempts + 1):
            try:
                raw = spec.func(**kwargs)
                if isinstance(raw, dict) and "status" in raw:
                    result = dict(raw)
                else:
                    result = {"status": "ok", "output": raw}
                result.setdefault("attempts", attempt)
                result.setdefault("risk", decision.risk)
                self.audit.record(name, result["status"], {"attempt": attempt, "risk": decision.risk})
                return result
            except Exception as exc:  # pragma: no cover - exercised by tests
                last_result = {"status": "error", "message": str(exc), "attempts": attempt, "risk": decision.risk}
                self.audit.record(name, "error", {"attempt": attempt, "risk": decision.risk})
        return last_result or {"status": "error", "message": "tool execution failed", "attempts": total_attempts, "risk": decision.risk}

    def execute_code(
        self,
        code: str,
        *,
        sandbox: IsolatedSandbox | None = None,
        approve: bool = False,
        allow_external: bool = False,
    ) -> dict[str, Any]:
        if sandbox is None or not sandbox.available():
            self.audit.record("execute_python", "unavailable", {"reason": "sandbox unavailable"})
            return {"status": "unavailable", "message": "isolated sandbox unavailable"}
        return self.execute_tool(
            "execute_python",
            code=code,
            sandbox=sandbox,
            approve=approve,
            allow_external=allow_external,
        )

    def verify_assertion(
        self,
        expression: str,
        expected: Any,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        actual = self.evaluator.evaluate(expression, context=context)
        return {
            "status": "ok",
            "actual": actual,
            "expected": expected,
            "matched": actual == expected,
            "message": "assertion matched" if actual == expected else f"expected {expected!r}, got {actual!r}",
        }

    def retrieve_literature(
        self,
        query: str,
        *,
        backend: RetrievalBackend | None = None,
        approve: bool = False,
        allow_external: bool = False,
    ) -> dict[str, Any]:
        if backend is None:
            self.audit.record("retrieve_literature", "unavailable", {"query": query[:120]})
            return {"status": "unavailable", "query": query, "results": [], "message": "retrieval backend unavailable"}
        return self.execute_tool(
            "retrieve_literature",
            query=query,
            backend=backend,
            approve=approve,
            allow_external=allow_external,
        )

    def run(
        self,
        goal: str,
        *,
        approve: bool = False,
        allow_external: bool = False,
        retrieval_backend: RetrievalBackend | None = None,
        sandbox: IsolatedSandbox | None = None,
        arithmetic_assertion: str | None = None,
        expected_value: Any | None = None,
    ) -> dict[str, Any]:
        allowed, issues = self.guardrail.screen(goal)
        if not allowed:
            self.audit.record("plan", "blocked", {"reason_count": len(issues)})
            return {
                "status": "blocked",
                "approved": False,
                "goal": goal,
                "issues": list(issues),
                "audit": self.audit.entries,
            }

        plan = self.plan(goal, request_retrieval=retrieval_backend is not None, request_execution=sandbox is not None)
        retrieval = self.retrieve_literature(goal, backend=retrieval_backend, approve=approve, allow_external=allow_external)
        assertion = None
        if arithmetic_assertion is not None:
            assertion = self.verify_assertion(arithmetic_assertion, expected_value)
        code_execution = None
        if sandbox is not None:
            code_execution = self.execute_code("result = 1", sandbox=sandbox, approve=approve, allow_external=allow_external)

        evidence = retrieval.get("results", []) if retrieval.get("status") == "ok" else []
        hypotheses = [{
            "statement": goal,
            "status": "supported" if evidence else "needs_evidence",
            "kind": "hypothesis",
        }]
        uncertainty = []
        if retrieval.get("status") != "ok":
            uncertainty.append(retrieval.get("message", "retrieval unavailable"))
        if code_execution and code_execution.get("status") != "ok":
            uncertainty.append(code_execution.get("message", "sandbox unavailable"))
        if assertion and not assertion["matched"]:
            uncertainty.append(assertion["message"])

        summary = self.execute_tool(
            "summarize",
            goal=goal,
            hypotheses=hypotheses,
            evidence=evidence,
            uncertainty=uncertainty,
            approve=True,
            allow_external=False,
        )
        status = "ok"
        for candidate in (retrieval, code_execution):
            if candidate and candidate.get("status") in {"pending_approval", "disabled", "blocked", "rejected", "error"}:
                status = candidate["status"]
                break
        return {
            "status": status,
            "approved": status == "ok",
            "goal": goal,
            "plan": plan.to_dict(),
            "hypotheses": hypotheses,
            "evidence": evidence,
            "retrieval": retrieval,
            "assertion": assertion,
            "code_execution": code_execution,
            "summary": summary.get("output") if summary.get("status") == "ok" else summary,
            "uncertainty": uncertainty,
            "audit": self.audit.entries,
        }

    def _memory_lookup(self, query: str) -> dict[str, Any]:
        return {"query": query, "matches": []}

    def _retrieve_literature(self, query: str, backend: RetrievalBackend) -> dict[str, Any]:
        documents = backend.search(query)
        results = []
        for document in documents:
            normalized = {
                "title": document.get("title", ""),
                "snippet": document.get("snippet", ""),
            }
            if document.get("citation"):
                normalized["citation"] = document["citation"]
            if document.get("uri"):
                normalized["uri"] = document["uri"]
            results.append(normalized)
        return {"status": "ok", "query": query, "results": results, "message": "retrieval completed"}

    def _execute_python(self, code: str, sandbox: IsolatedSandbox) -> dict[str, Any]:
        result = dict(sandbox.execute(code))
        result.setdefault("status", "ok")
        return result

    def _safe_assert(self, expression: str, expected: Any, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self.verify_assertion(expression, expected, context=context)

    def _summarize(
        self,
        goal: str,
        hypotheses: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        uncertainty: list[str],
    ) -> dict[str, Any]:
        return {
            "goal": goal,
            "hypotheses": hypotheses,
            "evidence_count": len(evidence),
            "uncertainty": uncertainty,
        }
