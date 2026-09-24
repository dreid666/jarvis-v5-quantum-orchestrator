"""Validation tests for skill frontmatter and Markdown structure."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATHS = (
    ROOT / ".github" / "skills" / "code-review" / "SKILL.md",
    ROOT / ".github" / "skills" / "ai-research" / "SKILL.md",
)


def _frontmatter_map(path: Path) -> dict[str, object]:
    text = path.read_text()
    assert text.startswith("---\n")
    _, frontmatter, _ = text.split("---\n", 2)
    data = yaml.safe_load(frontmatter)
    assert isinstance(data, dict)
    return data


def test_skill_files_have_frontmatter_and_balanced_fences():
    for path in SKILL_PATHS:
        frontmatter = _frontmatter_map(path)
        text = path.read_text()
        assert frontmatter["name"]
        assert frontmatter["description"]
        assert "~~~" not in text
        assert text.count("```") % 2 == 0


def test_code_review_skill_is_narrowly_scoped():
    text = SKILL_PATHS[0].read_text().casefold()
    banned_patterns = (
        r"ai co-scientist",
        r"qml architect",
        r"robotic lab",
        r"\brag\b",
        r"python framework",
        r"\borchestration\b",
    )
    for banned in banned_patterns:
        assert re.search(banned, text) is None


def test_ai_research_skill_requires_real_citations_and_approval():
    text = SKILL_PATHS[1].read_text().casefold()
    assert "citation" in text
    assert "explicit human approval" in text
    assert "retrieval is unavailable" in text or "if retrieval is unavailable" in text
