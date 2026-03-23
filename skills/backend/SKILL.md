---
name: backend
description: Build or modify backend services with correctness, observability, and testability in mind.
version: "1"
summary: Use when working on APIs, services, handlers, queues, persistence, or server-side workflows.
tags: [backend, api, service]
triggers: [backend, api, service, handler, endpoint, repository, persistence, database, contract]
constraints:
  - Preserve explicit contracts at module boundaries.
  - Favor deterministic behavior and test coverage over cleverness.
stop_conditions:
  - The change path and verification path are both clear.
---

# Backend Skill

1. Start from the data flow: input, validation, domain logic, output.
2. Add or update tests close to the changed behavior.
3. Keep side effects observable through logs, metrics, or return values.
4. If persistence changes, consider backward compatibility and migrations.
5. Never hide failing behavior behind silent fallbacks.

Reference files:
- `references/contracts.md` for contract-first backend checks.
