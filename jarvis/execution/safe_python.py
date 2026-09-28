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
        "round": round,
        "pow": pow,
    }
    MAX_SEQUENCE_ITEMS = 32
    MAX_ABS_NUMBER = 1_000_000
    MAX_POW_EXPONENT = 100
    MAX_CALL_ARGS = 8

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
            if type(node.value) not in (int, float, bool):
                raise ValueError("unsupported constant type")
            if isinstance(node.value, (int, float)) and abs(node.value) > self.MAX_ABS_NUMBER:
                raise ValueError("numeric literal too large")
            return node.value
        if isinstance(node, ast.Name):
            if node.id in context:
                value = context[node.id]
                self._validate_scalar(value)
                return value
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
                self._validate_pow_operands(left, right)
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
            if node.keywords:
                raise ValueError("keyword arguments are not allowed")
            args = [self._eval_node(arg, context) for arg in node.args]
            return self._invoke_safe_function(func_name, args)
        if isinstance(node, ast.Tuple):
            if len(node.elts) > self.MAX_SEQUENCE_ITEMS:
                raise ValueError("sequence too large")
            return tuple(self._eval_node(item, context) for item in node.elts)
        if isinstance(node, ast.List):
            if len(node.elts) > self.MAX_SEQUENCE_ITEMS:
                raise ValueError("sequence too large")
            return [self._eval_node(item, context) for item in node.elts]
        raise ValueError(f"syntax not allowed: {type(node).__name__}")

    def _validate_scalar(self, value: Any) -> None:
        if type(value) not in (int, float, bool):
            raise ValueError("unsupported value type")
        if isinstance(value, (int, float)) and abs(value) > self.MAX_ABS_NUMBER:
            raise ValueError("numeric value too large")

    def _validate_pow_operands(self, left: Any, right: Any) -> None:
        self._validate_scalar(left)
        self._validate_scalar(right)
        if abs(right) > self.MAX_POW_EXPONENT:
            raise ValueError("exponent too large")

    def _validate_numeric_args(self, args: list[Any], *, min_args: int, max_args: int) -> None:
        if not (min_args <= len(args) <= max_args):
            raise ValueError("invalid argument count")
        for value in args:
            self._validate_scalar(value)

    def _validate_collection_arg(self, value: Any) -> list[Any]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("expected a list or tuple")
        if len(value) > self.MAX_SEQUENCE_ITEMS:
            raise ValueError("sequence too large")
        items = list(value)
        for item in items:
            self._validate_scalar(item)
        return items

    def _invoke_safe_function(self, name: str, args: list[Any]) -> Any:
        if len(args) > self.MAX_CALL_ARGS:
            raise ValueError("too many arguments")
        if name == "abs":
            self._validate_numeric_args(args, min_args=1, max_args=1)
        elif name == "round":
            if len(args) not in {1, 2}:
                raise ValueError("invalid argument count")
            self._validate_scalar(args[0])
            if len(args) == 2:
                if type(args[1]) is not int or abs(args[1]) > 12:
                    raise ValueError("invalid round precision")
        elif name == "pow":
            if len(args) != 2:
                raise ValueError("pow requires exactly two arguments")
            self._validate_pow_operands(args[0], args[1])
        elif name in {"min", "max"}:
            if len(args) == 1:
                args = self._validate_collection_arg(args[0])
            else:
                self._validate_numeric_args(args, min_args=2, max_args=self.MAX_CALL_ARGS)
        else:
            raise ValueError(f"function not allowed: {name}")
        return self.SAFE_FUNCS[name](*args)
