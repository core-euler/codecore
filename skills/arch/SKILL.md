---
name: arch
description: Design architectures, boundaries, and decision records with explicit tradeoffs.
version: "1"
summary: Use when the task is about architecture, system design, module boundaries, or ADR-level choices.
tags: [architecture, design]
triggers: [architecture, architect, adr, boundary, boundaries, design, system design, module]
constraints:
  - Make architectural tradeoffs explicit.
  - Prefer stable interfaces over incidental coupling.
stop_conditions:
  - Decision options and consequences are documented.
---

# Architecture Skill

1. Define the problem boundary before proposing structure.
2. Separate domain, orchestration, and infrastructure concerns.
3. Call out tradeoffs, migration cost, and failure modes.
4. Prefer contracts and composition over cross-layer shortcuts.
5. If a decision is irreversible or expensive, recommend an ADR.

Reference files:
- `references/boundaries.md` for boundary review heuristics.
