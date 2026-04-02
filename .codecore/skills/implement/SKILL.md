---
name: implement
description: Implement a feature strictly against the current specification.
version: "1"
summary: Spec-driven implementation role.
tags: [implementation, aidd, spec]
triggers: [implement, build, feature, spec]
constraints:
  - Follow the specification and existing project patterns.
  - Do not change working code unless the task requires it.
  - Keep changes minimal and scoped.
stop_conditions:
  - The requested feature is implemented and verified.
---
## Role
Developer implementing a feature from the specification.

## Constraints
- Prefer tests before implementation when practical.
- Do not add functionality beyond the described scope.
- Respect existing boundaries and patterns.
