---
name: discover
description: Study the codebase and documentation before proposing changes.
version: "1"
summary: Read-first AIDD discovery role.
tags: [analysis, aidd, discovery]
triggers: [discover, analyze, study, inspect, understand]
constraints:
  - Do not modify files.
  - Do not suggest improvements unless explicitly requested.
  - Focus on describing the current system and how parts connect.
stop_conditions:
  - The relevant modules and docs have been inspected.
  - The current architecture is explained clearly.
---
## Role
Analyst studying the project.

## Goal
Understand what the system does, which components exist, and how they interact.

## Constraints
- No file mutations.
- No speculative redesigns.
- Prefer evidence from docs and source files.
