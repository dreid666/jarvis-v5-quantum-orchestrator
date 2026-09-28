---
name: code-review
description: "Use when reviewing repository changes for correctness, safety, and test coverage without performing unrelated research or orchestration work."
---

# Code Review

Review the proposed change set for concrete bugs, broken contracts, safety regressions, and missing validation.

## Scope

- Stay focused on the code or documentation being reviewed.
- Report high-confidence findings tied to specific files, behaviors, or tests.
- Do not replace review work with unrelated research-agent instructions.
- Do not claim a tool result, citation, or reproduction step unless it was actually performed.

## Review Workflow

1. Identify the changed files and the contract they affect.
2. Check correctness, safety boundaries, and approval or guardrail behavior.
3. Look for missing tests around new behavior, invalid input, and regressions.
4. Summarize only actionable findings, ordered by severity.

## Safety Rules

- Treat prompt or tool keyword matches as signals, not as the security boundary.
- Prefer existing repository guardrails, approval policy, and audit mechanisms over ad hoc deny lists.
- Never recommend `exec`, `eval`, fake retrieval, or fabricated citations for untrusted input.
- If evidence is incomplete, say so explicitly.

## Output Format

For each finding include:

- severity
- affected file or interface
- concise explanation of the bug or risk
- validation gap or failing scenario
