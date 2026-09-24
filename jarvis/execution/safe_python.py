"""Safe Python evaluation without exec/eval."""

from __future__ import annotations

import ast
from typing import Any, Mapping


class SafePythonEvaluator:
    """Safely evaluate a narrow subset of Python expressions and assignments."""

    SAFE_FUNCS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "pow": pow,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }

    def evaluate(self, expr: str, context: Mapping[str, Any] | None = None) -> Any:
        if not isinstance(expr, str):
            raise ValueError("expression must be a string")
        try:
            tree = ast.parse(expr, mode="eval")
            return self._eval_node(tree.body, dict(context or {}))
        except SyntaxError as exc:
            raise ValueError(f"invalid syntax: {exc}") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"evaluation failed: {exc}") from exc

    def evaluate_statement(self, statement: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(statement, str):
            raise ValueError("statement must be a string")
        try:
            tree = ast.parse(statement, mode="exec")
        except SyntaxError as exc:
            raise ValueError(f"invalid syntax: {exc}") from exc

        local_env = dict(context or {})
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ValueError("only simple assignment statements are allowed")
            local_env[node.targets[0].id] = self._eval_node(node.value, local_env)
        return local_env

    def _eval_node(self, node: ast.AST, env: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, bool, str):
                raise ValueError("unsupported constant type")
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            if node.id in self.SAFE_FUNCS:
                return self.SAFE_FUNCS[node.id]
            raise ValueError(f"name not allowed: {node.id}")
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, env)
            right = self._eval_node(node.right, env)
            operators = {
                ast.Add: lambda a, b: a + b,
                ast.Sub: lambda a, b: a - b,
                ast.Mult: lambda a, b: a * b,
                ast.Div: lambda a, b: a / b,
                ast.FloorDiv: lambda a, b: a // b,
                ast.Mod: lambda a, b: a % b,
                ast.Pow: lambda a, b: a**b,
            }
            for operator, func in operators.items():
                if type(node.op) is operator:
                    return func(left, right)
            raise ValueError("operator not allowed")
        if isinstance(node, ast.UnaryOp):
            value = self._eval_node(node.operand, env)
            if type(node.op) is ast.UAdd:
                return +value
            if type(node.op) is ast.USub:
                return -value
            if type(node.op) is ast.Not:
                return not value
            raise ValueError("unary operator not allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only direct function calls are allowed")
            if node.keywords:
                raise ValueError("keyword arguments are not allowed")
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCS:
                raise ValueError(f"function not allowed: {func_name}")
            args = [self._eval_node(arg, env) for arg in node.args]
            return self.SAFE_FUNCS[func_name](*args)
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item, env) for item in node.elts)
        if isinstance(node, ast.List):
            return [self._eval_node(item, env) for item in node.elts]
        if isinstance(node, ast.Set):
            return {self._eval_node(item, env) for item in node.elts}
        if isinstance(node, ast.Dict):
            return {
                self._eval_node(key, env): self._eval_node(value, env)
                for key, value in zip(node.keys, node.values)
            }
        raise ValueError(f"syntax not allowed: {type(node).__name__}")
