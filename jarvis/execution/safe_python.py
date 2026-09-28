"""Safe Python evaluation without exec/eval."""

from __future__ import annotations

import ast
from typing import Any, Mapping, Optional


class SafePythonEvaluator:
    """Safely evaluate arithmetic expressions and simple assignments."""

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

    def evaluate(self, expr: str, context: Optional[dict[str, Any]] = None) -> Any:
        if not isinstance(expr, str) or not expr.strip():
            raise ValueError("expression must be a non-empty string")
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"invalid syntax: {exc}") from exc
        return self._eval_node(tree.body, dict(context or {}))

    def evaluate_statement(self, statement: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError("statement must be a non-empty string")
        try:
            tree = ast.parse(statement, mode="exec")
        except SyntaxError as exc:
            raise ValueError(f"invalid syntax: {exc}") from exc
        local_env = dict(context or {})
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                raise ValueError("only assignment statements are allowed")
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ValueError("only simple assignment is allowed")
            local_env[node.targets[0].id] = self._eval_node(node.value, local_env)
        return local_env

    def _eval_node(self, node: ast.AST, context: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, bool, str):
                raise ValueError("unsupported constant type")
            return node.value
        if isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            if node.id in self.SAFE_FUNCS:
                return self.SAFE_FUNCS[node.id]
            raise ValueError(f"name not allowed: {node.id}")
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
            if type(node.op) is ast.Pow:
                return left ** right
            if type(node.op) is ast.FloorDiv:
                return left // right
            if type(node.op) is ast.Mod:
                return left % right
            raise ValueError("operator not allowed")
        if isinstance(node, ast.UnaryOp):
            value = self._eval_node(node.operand, context)
            if type(node.op) is ast.UAdd:
                return +value
            if type(node.op) is ast.USub:
                return -value
            raise ValueError("unary operator not allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only direct function calls are allowed")
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCS:
                raise ValueError(f"function not allowed: {func_name}")
            args = [self._eval_node(arg, context) for arg in node.args]
            return self.SAFE_FUNCS[func_name](*args)
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item, context) for item in node.elts)
        if isinstance(node, ast.List):
            return [self._eval_node(item, context) for item in node.elts]
        raise ValueError(f"syntax not allowed: {type(node).__name__}")
