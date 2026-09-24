---
name: code-review
description: Provide narrowly scoped code review guidance that focuses on correctness, regressions, security, and test coverage in repository changes.
---

# Code Review

Use this skill only for reviewing code changes.

## Review Focus

1. Confirm the change matches the requested behavior and stays within scope.
2. Look for correctness bugs, regressions, missing edge-case handling, and unsafe behavior.
3. Check whether changed tests cover the new behavior and whether existing tests still make sense.
4. Flag missing validation, broken contracts, or incorrect assumptions in modified code paths.

## Review Output

- Report only actionable findings backed by the diff or surrounding code.
- Prioritize security, data-loss, reliability, and logic issues over style concerns.
- Explain the user-visible impact and the minimal fix when possible.
- If no high-confidence issue is found, say so plainly.
