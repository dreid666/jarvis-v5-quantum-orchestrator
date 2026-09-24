---
name: ai-research
description: Plan AI-assisted research workflows with explicit source handling, simulation-first execution, and human approval gates for external actions.
---

# AI Research

Use this skill for planning or reviewing AI-assisted research workflows.

## Default Operating Mode

- Default to planning, simulation, and offline analysis.
- Treat provider-backed execution, external systems, and physical or robotic actions as opt-in only.
- Require explicit human approval before any external, provider-backed, or physical action is proposed for execution.

## Retrieval and Literature Guidance

1. Separate hypotheses, assumptions, and retrieved evidence.
2. Report retrieval results only when actual source metadata is available.
3. Every cited result must carry usable source metadata such as title, identifier, URL, or equivalent citation details.
4. If retrieval is unavailable, incomplete, or unverified, state that explicitly instead of implying grounded support.
5. Do not fabricate references, citations, benchmark claims, or verification status.

## Planning Guidance

1. Break work into reviewable steps with clear inputs, outputs, and safety assumptions.
2. Mark code execution, provider APIs, lab systems, and hardware control as high risk.
3. Keep speculative analysis separate from validated observations.
4. Prefer reproducible simulation plans and clearly label any follow-up work that would require approval or infrastructure.

## Deliverables

- A structured hypothesis or research question.
- A simulation-first validation plan.
- A list of required evidence or retrieval gaps.
- Explicit approval requirements for any external execution path.
