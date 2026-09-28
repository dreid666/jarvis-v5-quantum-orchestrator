from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, body = text.split("---\n", 2)
    data = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data, body


def test_code_review_skill_has_valid_frontmatter_and_scope():
    frontmatter, body = _load_frontmatter(ROOT / ".github/skills/code-review/SKILL.md")
    assert frontmatter["name"] == "code-review"
    assert "description" in frontmatter
    assert "code review" in body.lower()
    assert "co-scientist" not in body.lower()
    assert "integrated python framework" not in body.lower()
    assert body.count("```") % 2 == 0


def test_research_skill_and_agent_documents_have_expected_shape():
    skill_frontmatter, skill_body = _load_frontmatter(ROOT / ".github/skills/research-orchestration/SKILL.md")
    agent_frontmatter, agent_body = _load_frontmatter(ROOT / ".github/agents/research-workflow.agent.md")

    assert skill_frontmatter["name"] == "research-orchestration"
    assert "hypotheses" in skill_body.lower()
    assert "approval" in skill_body.lower()
    assert "unavailable" in skill_body.lower()
    assert skill_body.count("```") % 2 == 0

    assert agent_frontmatter["name"] == "Research Workflow Agent"
    assert ".github/skills/research-orchestration/SKILL.md" in agent_body
    assert "authorized tools" in agent_body.lower()
