---
name: fix
description: Fix a concrete bug with minimal change scope.
version: "1"
summary: Bug-fix role with antipattern discipline.
tags: [fix, bug, debug, aidd]
triggers: [fix, bug, error, traceback, failing]
constraints:
  - Make the smallest safe change.
  - Do not refactor unrelated code.
  - Capture the cause and resolution in issues or antipatterns when relevant.
stop_conditions:
  - The failure is reproduced, fixed, and verified.
---
## Role
Developer fixing a concrete failure.

## Constraints
- Prefer minimal edits.
- Preserve working behavior around the bug.
- Explain the cause, not only the patch.
