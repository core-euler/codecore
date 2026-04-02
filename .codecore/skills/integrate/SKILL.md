---
name: integrate
description: Connect a new component into an existing system safely.
version: "1"
summary: Integration role for connecting existing parts.
tags: [integrate, integration, wiring, aidd]
triggers: [integrate, connect, wire, hook]
constraints:
  - Keep existing components stable.
  - Change only integration points unless explicitly instructed otherwise.
  - Follow established project conventions.
stop_conditions:
  - The new component is wired in and verified.
---
## Role
Developer integrating a new component into the system.

## Constraints
- Avoid refactoring existing modules unless necessary for the connection point.
- Prefer the project's established extension seams.
- Verify the integration path after changes.
