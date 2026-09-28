---
name: research-orchestration
description: "Use when planning or reviewing safe research workflows that separate evidence from hypotheses, keep execution deterministic by default, and require approval for external side effects."
---

# Research Orchestration

Plan research work without pretending that unavailable tools, provider calls, robotics, or scientific results already exist.

## Scope

- Generate hypotheses, plans, and uncertainty-aware reports.
- Distinguish clearly between observed evidence, repository-local context, and open questions.
- Keep local deterministic execution as the default mode.

## Safety Boundaries

- Use only explicitly authorized tools.
- External retrieval, provider-backed inference, robotic control, hardware execution, and file or network side effects require explicit opt-in and approval.
- If an isolated sandbox or retrieval backend is unavailable, report `unavailable` rather than inventing a result.
- Do not present simulated output as proof of real-world or quantum-hardware performance.

## Verification Requirements

1. Screen the goal with the repository guardrail before planning or execution.
2. Record risky actions through the repository approval and audit flow.
3. Verify arithmetic or symbolic checks with a safe AST-based evaluator, not `exec` or `eval` on untrusted input.
4. Report uncertainty whenever evidence is missing, external actions were blocked, or a capability is unavailable.

## Implementation Contract

A conforming implementation should:

- return a reviewable plan with named actions and risk levels;
- keep hypotheses and evidence in separate fields;
- fail closed for unapproved or unauthorized tools;
- return explicit `unavailable`, `pending_approval`, `disabled`, or `blocked` states when appropriate;
- include only real retrieval outputs from a supplied backend.
