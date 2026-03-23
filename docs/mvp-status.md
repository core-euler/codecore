# CodeCore MVP Status

## Status
Accepted

## Date
2026-03-23

## Statement
CodeCore is now considered a personally testable MVP.

This means the system is ready for real operator-driven testing on actual development tasks and repositories, with the expectation that findings from this testing phase will shape the next hardening iterations.

## What This Status Means
- The product is no longer only a design or architecture exercise.
- The runtime is functional end-to-end and can be used interactively.
- The system is suitable for personal dogfooding and structured benchmark runs.
- Core engineering loops exist in working form: prompt, context, routing, execution, verification, rollback, telemetry, and multi-agent delegation.

## Current Functional Baseline
- REPL runtime with provider routing and fallback.
- Manifest-driven project, provider, skill, and MCP loading.
- Context assembly with budget control, repo map, pinned files, and skill composition.
- Metadata-first memory, recall, rankings, and analytics.
- Managed execution commands including `/run`, `/verify`, `/replace`, `/rollback`, `/autoedit`, `/delegate`, and `/benchmark`.
- Approval flow, audit trail, and security guardrails for untrusted content and secret hygiene.

## Evidence
- Automated test suite is passing.
- Package build is passing.
- Phase 1 through Phase 6 are implemented in runnable form.
- Phase 7 has started with a security hardening baseline.

## Intended Use At This Stage
- Personal testing by the project owner.
- Real development sessions on non-critical repositories.
- Comparative testing across different model providers and aliases.
- Evaluation of how well the environment normalizes outcomes across models.

## Explicit Non-Goals At This Stage
- Production release for external users.
- Stability guarantees across all environments and providers.
- Fully hardened security and governance posture.
- Final benchmark proof across all target model classes.

## Exit Criteria For MVP Status
The project should leave the "personally testable MVP" stage only after the following are complete:
- Repeated successful dogfooding sessions on real repositories.
- Benchmark evidence across multiple real model backends.
- CI and regression gates for build, tests, and packaging.
- Additional hardening for security, approvals, and failure recovery.
- Release packaging and operational documentation suitable for external use.
