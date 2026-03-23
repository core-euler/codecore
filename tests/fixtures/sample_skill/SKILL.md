---
name: architecture-review
description: Review architecture decisions and identify weak boundaries.
version: "1"
summary: Architecture review workflow.
tags: [architecture, review]
triggers: [adr, architecture, boundary]
constraints:
  - Do not modify runtime files directly.
stop_conditions:
  - Findings list is produced.
---

# Architecture Review

Use this skill when the task is about architectural integrity.
