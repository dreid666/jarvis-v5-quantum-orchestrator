"""Security and guardrail helpers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    issues: tuple[str, ...]


class PromptGuardrail:
    """Deny-by-default safety screening for untrusted prompt text."""

    MAX_PROMPT_CHARS = 12000
    DISALLOWED_PATTERNS = (
        "ignore all previous",
        "override system",
        "developer mode",
        "do anything now",
        "bypass policy",
        "jailbreak",
    )

    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            raise ValueError("prompt must be a string")
        value = unicodedata.normalize("NFKC", text).strip()
        return re.sub(r"[^\S\n]+", " ", value)

    def screen(self, prompt: str) -> tuple[bool, tuple[str, ...]]:
        text = self.normalize(prompt)
        issues: list[str] = []

        if not text:
            issues.append("empty prompt")
        if len(text) > self.MAX_PROMPT_CHARS:
            issues.append("prompt exceeds maximum length")

        lowered = text.casefold()
        for pattern in self.DISALLOWED_PATTERNS:
            if pattern in lowered:
                issues.append(f"contains disallowed pattern: {pattern}")

        if text.count("\n") > 20:
            issues.append("prompt contains excessive newlines")

        return not issues, tuple(issues)
