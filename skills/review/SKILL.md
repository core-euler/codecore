---
name: review
description: Review code changes for bugs, regressions, missing tests, and weak assumptions.
version: "1"
summary: Use when the task is to inspect a change, audit risk, or validate implementation quality.
tags: [review, audit]
triggers: [review, audit, regression, bug, inspect, findings]
constraints:
  - Findings come before summaries.
  - Focus on behavioral risk, not stylistic taste.
stop_conditions:
  - Actionable findings or explicit no-findings conclusion is produced.
---

# Review Skill

1. Look for correctness bugs, missing validation, and state inconsistencies.
2. Check whether tests cover the changed behavior and edge cases.
3. Call out assumptions that are not enforced by code.
4. Prefer concrete evidence: file, line, scenario, and user impact.
5. If no findings exist, state remaining risks or testing gaps.

Reference files:
- `references/findings.md` for compact findings structure.
