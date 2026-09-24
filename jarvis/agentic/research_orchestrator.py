"""Approval-aware research orchestration primitives for JARVIS."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from jarvis.security.guardrails import PromptGuardrail


@dataclass(frozen=True)
class RetrievalDocument:
    """Retrieved document with source metadata."""

    title: str
    citation: str
    uri: str = ""
    snippet: str = ""


@dataclass(frozen=True)
class RetrievalResult:
    """Structured retrieval response."""

    available: bool
    documents: tuple[RetrievalDocument, ...]
    message: str


class RetrievalProvider(Protocol):
    """Provider interface for retrieval-backed evidence lookup."""

    def search(self, query: str, *, limit: int = 3) -> RetrievalResult:
        """Return real documents with citations or an explicit unavailable result."""


class NullRetrievalProvider:
    """Fail-closed retrieval provider used when no backend is configured."""

    def search(self, query: str, *, limit: int = 3) -> RetrievalResult:
        return RetrievalResult(
            available=False,
            documents=(),
            message=(
                "Retrieval backend unavailable; no source-backed literature results were returned "
                f"for query {query!r}."
            ),
        )


@dataclass(frozen=True)
class SandboxRunResult:
    """Result returned by a sandbox backend."""

    available: bool
    success: bool
    summary: str
    output: Any = None
    stderr: str = ""


class SandboxRunner(Protocol):
    """Interface for isolated code execution backends."""

    def run(self, code: str) -> SandboxRunResult:
        """Execute code in an isolated sandbox."""


class UnavailableSandboxRunner:
    """Fail-closed sandbox runner used when no backend is configured."""

    def run(self, code: str) -> SandboxRunResult:
        return SandboxRunResult(
            available=False,
            success=False,
            summary="Sandbox backend unavailable; code execution denied.",
            output=None,
            stderr="sandbox backend unavailable",
        )


class RestrictedExpressionEvaluator(ast.NodeVisitor):
    """Evaluate a narrow set of arithmetic expressions without exec/eval."""

    _ALLOWED_FUNCTIONS: dict[str, Callable[..., Any]] = {
        "abs": abs,
        "max": max,
        "min": min,
        "pow": pow,
        "round": round,
        "sqrt": math.sqrt,
        "sum": sum,
    }
    _ALLOWED_CONSTANTS: dict[str, Any] = {"e": math.e, "pi": math.pi}
    _ALLOWED_NODE_TYPES = (
        ast.Expression,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Load,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Call,
        ast.Name,
    )

    def evaluate(self, expression: str) -> Any:
        tree = ast.parse(expression, mode="eval")
        return self.visit(tree)

    def generic_visit(self, node: ast.AST) -> Any:
        if not isinstance(node, self._ALLOWED_NODE_TYPES):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        return super().generic_visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
        return node.value

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(item) for item in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(item) for item in node.elts)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self._ALLOWED_CONSTANTS:
            return self._ALLOWED_CONSTANTS[node.id]
        raise ValueError(f"name not allowed: {node.id}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        operators: dict[type[ast.AST], Callable[[Any, Any], Any]] = {
            ast.Add: lambda a, b: a + b,
            ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b,
            ast.Div: lambda a, b: a / b,
            ast.Mod: lambda a, b: a % b,
            ast.Pow: lambda a, b: a**b,
        }
        operator = operators.get(type(node.op))
        if operator is None:
            raise ValueError(f"operator not allowed: {type(node.op).__name__}")
        return operator(left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        value = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value
        raise ValueError(f"unary operator not allowed: {type(node.op).__name__}")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("attribute access is not allowed")
        if node.func.id not in self._ALLOWED_FUNCTIONS:
            raise ValueError(f"function not allowed: {node.func.id}")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        args = [self.visit(argument) for argument in node.args]
        return self._ALLOWED_FUNCTIONS[node.func.id](*args)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        raise ValueError("attribute access is not allowed")

    def visit_Import(self, node: ast.Import) -> Any:
        raise ValueError("imports are not allowed")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        raise ValueError("imports are not allowed")


@dataclass(frozen=True)
class AuthorizationDecision:
    """Auditable authorization outcome for a tool invocation."""

    tool_name: str
    allowed: bool
    risk: str
    reason: str
    trusted_mode: bool
    approval_granted: bool


@dataclass(frozen=True)
class PlannedToolCall:
    """Planned tool execution step."""

    step: str
    tool_name: str
    arguments: Mapping[str, Any]
    retry_arguments: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ToolExecutionResult:
    """Execution result for a single tool call."""

    status: str
    summary: str
    payload: Any
    authorization: AuthorizationDecision


@dataclass(frozen=True)
class TraceEntry:
    """Recorded execution trace entry."""

    step: str
    tool_name: str
    status: str
    summary: str
    authorization: AuthorizationDecision
    payload: Any = None


@dataclass(frozen=True)
class RunResult:
    """Structured top-level orchestration result."""

    success: bool
    summary: str
    trace: tuple[TraceEntry, ...]
    requires_replan: bool = False


@dataclass(frozen=True)
class RegisteredTool:
    handler: Callable[..., Any]
    capabilities: frozenset[str] = field(default_factory=frozenset)
    description: str = ""


class CapabilityAuthorizer:
    """Authorize tool invocations using an explicit allowlist and approvals."""

    HIGH_RISK_CAPABILITIES = frozenset({"code_execution", "physical_action", "provider_action"})

    def authorize(
        self,
        tool_name: str,
        tool: RegisteredTool | None,
        *,
        trusted_mode: bool,
        approved_actions: frozenset[str],
    ) -> AuthorizationDecision:
        if tool is None:
            return AuthorizationDecision(
                tool_name=tool_name,
                allowed=False,
                risk="unknown",
                reason="tool is not registered",
                trusted_mode=trusted_mode,
                approval_granted=False,
            )

        risk = "high" if tool.capabilities & self.HIGH_RISK_CAPABILITIES else "low"
        approval_granted = tool_name in approved_actions
        if risk == "high" and not trusted_mode:
            return AuthorizationDecision(
                tool_name=tool_name,
                allowed=False,
                risk=risk,
                reason="high-risk capability requires trusted mode",
                trusted_mode=trusted_mode,
                approval_granted=approval_granted,
            )
        if risk == "high" and not approval_granted:
            return AuthorizationDecision(
                tool_name=tool_name,
                allowed=False,
                risk=risk,
                reason="high-risk capability requires explicit approval",
                trusted_mode=trusted_mode,
                approval_granted=False,
            )
        return AuthorizationDecision(
            tool_name=tool_name,
            allowed=True,
            risk=risk,
            reason="authorized",
            trusted_mode=trusted_mode,
            approval_granted=approval_granted,
        )


class AuthorizedToolRegistry:
    """Registered tool execution with explicit authorization decisions."""

    def __init__(self, authorizer: CapabilityAuthorizer | None = None) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._authorizer = authorizer or CapabilityAuthorizer()

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        capabilities: tuple[str, ...] = (),
        description: str = "",
    ) -> None:
        self._tools[name] = RegisteredTool(handler=handler, capabilities=frozenset(capabilities), description=description)

    def execute(
        self,
        call: PlannedToolCall,
        *,
        trusted_mode: bool,
        approved_actions: frozenset[str],
    ) -> ToolExecutionResult:
        tool = self._tools.get(call.tool_name)
        authorization = self._authorizer.authorize(
            call.tool_name,
            tool,
            trusted_mode=trusted_mode,
            approved_actions=approved_actions,
        )
        if not authorization.allowed:
            return ToolExecutionResult(
                status="denied",
                summary=authorization.reason,
                payload=None,
                authorization=authorization,
            )
        assert tool is not None
        payload = tool.handler(**dict(call.arguments))
        status = "success"
        summary = "completed"
        if isinstance(payload, SandboxRunResult):
            if not payload.available:
                status = "unavailable"
            elif not payload.success:
                status = "failed"
            summary = payload.summary
        elif isinstance(payload, RetrievalResult):
            status = "success" if payload.available else "unavailable"
            summary = payload.message
        return ToolExecutionResult(status=status, summary=summary, payload=payload, authorization=authorization)


class ResearchOrchestrator:
    """Simulation-first orchestrator for approval-aware research workflows."""

    def __init__(
        self,
        *,
        retrieval_provider: RetrievalProvider | None = None,
        sandbox_runner: SandboxRunner | None = None,
        trusted_mode: bool = False,
        approved_actions: frozenset[str] | None = None,
        guardrail: PromptGuardrail | None = None,
    ) -> None:
        self.retrieval_provider = retrieval_provider or NullRetrievalProvider()
        self.sandbox_runner = sandbox_runner or UnavailableSandboxRunner()
        self.trusted_mode = trusted_mode
        self.approved_actions = approved_actions or frozenset()
        self.guardrail = guardrail or PromptGuardrail()
        self.evaluator = RestrictedExpressionEvaluator()
        self.tools = AuthorizedToolRegistry()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.tools.register("draft_research_plan", self._draft_research_plan, description="Create a planning-only research brief")
        self.tools.register("retrieve_literature", self._retrieve_literature, description="Retrieve source-backed documents")
        self.tools.register("verify_symbolic", self._verify_symbolic, description="Verify arithmetic with a restricted evaluator")
        self.tools.register(
            "execute_python",
            self._execute_python,
            capabilities=("code_execution",),
            description="Execute Python in an external sandbox",
        )

    def _draft_research_plan(self, query: str, domain_module: str) -> dict[str, Any]:
        return {
            "query": query,
            "domain_module": domain_module,
            "mode": "planning_only",
            "approval_required_for_external_actions": True,
        }

    def _retrieve_literature(self, query: str, limit: int = 3) -> RetrievalResult:
        return self.retrieval_provider.search(query, limit=limit)

    def _verify_symbolic(self, expression: str, expected: Any | None = None) -> dict[str, Any]:
        value = self.evaluator.evaluate(expression)
        return {"value": value, "matches_expected": expected is None or value == expected}

    def _execute_python(self, code: str) -> SandboxRunResult:
        return self.sandbox_runner.run(code)

    def execute_plan(self, plan: tuple[PlannedToolCall, ...]) -> RunResult:
        trace: list[TraceEntry] = []
        for call in plan:
            result = self.tools.execute(
                call,
                trusted_mode=self.trusted_mode,
                approved_actions=self.approved_actions,
            )
            trace.append(
                TraceEntry(
                    step=call.step,
                    tool_name=call.tool_name,
                    status=result.status,
                    summary=result.summary,
                    authorization=result.authorization,
                    payload=result.payload,
                )
            )
            if result.status == "success":
                continue
            if result.status == "failed" and call.retry_arguments is not None:
                retry_call = PlannedToolCall(call.step, call.tool_name, call.retry_arguments)
                retry_result = self.tools.execute(
                    retry_call,
                    trusted_mode=self.trusted_mode,
                    approved_actions=self.approved_actions,
                )
                trace.append(
                    TraceEntry(
                        step=f"{call.step}:retry",
                        tool_name=call.tool_name,
                        status="retry_succeeded" if retry_result.status == "success" else "retry_failed",
                        summary=retry_result.summary,
                        authorization=retry_result.authorization,
                        payload=retry_result.payload,
                    )
                )
                if retry_result.status == "success":
                    continue
            return RunResult(
                success=False,
                summary=f"Execution requires replanning after step {call.step}: {result.summary}",
                trace=tuple(trace),
                requires_replan=True,
            )
        return RunResult(success=True, summary="Execution completed successfully.", trace=tuple(trace))

    def run(self, user_query: str, domain_module: str = "ai_research") -> RunResult:
        allowed, issues = self.guardrail.screen(user_query)
        if not allowed:
            authorization = AuthorizationDecision(
                tool_name="guardrail",
                allowed=False,
                risk="low",
                reason=", ".join(issues),
                trusted_mode=self.trusted_mode,
                approval_granted=False,
            )
            return RunResult(
                success=False,
                summary="Input blocked by prompt guardrail.",
                trace=(
                    TraceEntry(
                        step="guardrail",
                        tool_name="guardrail",
                        status="denied",
                        summary=authorization.reason,
                        authorization=authorization,
                    ),
                ),
                requires_replan=False,
            )
        plan = (
            PlannedToolCall(
                step="draft-plan",
                tool_name="draft_research_plan",
                arguments={"query": user_query, "domain_module": domain_module},
            ),
        )
        return self.execute_plan(plan)
