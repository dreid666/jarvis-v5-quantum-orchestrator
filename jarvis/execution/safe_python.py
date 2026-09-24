"""Safe Python evaluation without exec/eval."""

from __future__ import annotations

import ast
from typing import Any, Mapping


class SafePythonEvaluator:
    """Safely evaluate small arithmetic expressions without exec/eval."""

    SAFE_FUNCS = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "round": round,
        "pow": pow,
        "int": int,
        "float": float,
        "bool": bool,
    }
    MAX_INT_ABS = 10**6
    MAX_COLLECTION_SIZE = 10_000
    MAX_POWER_EXPONENT = 8

    def evaluate(
        self,
        expr: str,
        context: Mapping[str, Any] | None = None,
        *,
        env: Mapping[str, Any] | None = None,
    ) -> Any:
        if not isinstance(expr, str):
            raise ValueError("expression must be a string")
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"invalid syntax: {exc}") from exc
        return self._eval_node(tree.body, self._coerce_env(context=context, env=env))

    def evaluate_statement(
        self,
        statement: str,
        context: Mapping[str, Any] | None = None,
        *,
        env: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(statement, str):
            raise ValueError("statement must be a string")
        try:
            tree = ast.parse(statement, mode="exec")
        except SyntaxError as exc:
            raise ValueError(f"invalid syntax: {exc}") from exc
        local_env = dict(self._coerce_env(context=context, env=env))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                raise ValueError("only assignment statements are allowed")
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ValueError("only simple assignment is allowed")
            local_env[node.targets[0].id] = self._eval_node(node.value, local_env)
        return local_env

    def _coerce_env(
        self,
        *,
        context: Mapping[str, Any] | None,
        env: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if context is not None and env is not None:
            raise ValueError("provide either context or env, not both")
        return dict(env or context or {})

    def _eval_node(self, node: ast.AST, env: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, bool, str):
                raise ValueError("unsupported constant type")
            return self._bounded(node.value)
        if isinstance(node, ast.Name):
            if node.id in env:
                return self._bounded(env[node.id])
            if node.id in self.SAFE_FUNCS:
                return self.SAFE_FUNCS[node.id]
            raise ValueError(f"name not allowed: {node.id}")
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, env)
            right = self._eval_node(node.right, env)
            if type(node.op) is ast.Add:
                return self._bounded(left + right)
            if type(node.op) is ast.Sub:
                return self._bounded(left - right)
            if type(node.op) is ast.Mult:
                return self._multiply(left, right)
            if type(node.op) is ast.Div:
                return self._bounded(left / right)
            if type(node.op) is ast.Pow:
                return self._power(left, right)
            raise ValueError("operator not allowed")
        if isinstance(node, ast.UnaryOp):
            value = self._eval_node(node.operand, env)
            if type(node.op) is ast.UAdd:
                return self._bounded(+value)
            if type(node.op) is ast.USub:
                return self._bounded(-value)
            raise ValueError("unary operator not allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only direct function calls are allowed")
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCS:
                raise ValueError(f"function not allowed: {func_name}")
            args = [self._eval_node(arg, env) for arg in node.args]
            return self._bounded(self.SAFE_FUNCS[func_name](*args))
        if isinstance(node, ast.Tuple):
            return tuple(self._bounded(self._eval_node(item, env)) for item in node.elts)
        if isinstance(node, ast.List):
            return [self._bounded(self._eval_node(item, env)) for item in node.elts]
        raise ValueError(f"syntax not allowed: {type(node).__name__}")

    def _multiply(self, left: Any, right: Any) -> Any:
        if isinstance(left, list) and isinstance(right, int):
            if right < 0 or len(left) * right > self.MAX_COLLECTION_SIZE:
                raise ValueError("collection result too large")
            return left * right
        if isinstance(right, list) and isinstance(left, int):
            if left < 0 or len(right) * left > self.MAX_COLLECTION_SIZE:
                raise ValueError("collection result too large")
            return right * left
        return self._bounded(left * right)

    def _power(self, left: Any, right: Any) -> Any:
        if not isinstance(right, int):
            raise ValueError("power exponent must be an integer")
        if abs(right) > self.MAX_POWER_EXPONENT:
            raise ValueError("power exponent too large")
        return self._bounded(left ** right)

    def _bounded(self, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if abs(value) > self.MAX_INT_ABS:
                raise ValueError("numeric result too large")
            return value
        if isinstance(value, float):
            if abs(value) > float(self.MAX_INT_ABS):
                raise ValueError("numeric result too large")
            return value
        if isinstance(value, str):
            if len(value) > self.MAX_COLLECTION_SIZE:
                raise ValueError("string result too large")
            return value
        if isinstance(value, tuple):
            if len(value) > self.MAX_COLLECTION_SIZE:
                raise ValueError("collection result too large")
            return tuple(self._bounded(item) for item in value)
        if isinstance(value, list):
            if len(value) > self.MAX_COLLECTION_SIZE:
                raise ValueError("collection result too large")
            return [self._bounded(item) for item in value]
        return value
