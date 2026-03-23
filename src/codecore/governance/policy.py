"""Command policy evaluation for execution tools."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from ..domain.contracts import PolicyEngine
from ..domain.enums import PolicyAction, RiskLevel
from ..domain.results import PolicyDecision

_READ_ONLY = {"pwd", "ls", "find", "cat", "sed", "head", "tail", "rg", "git", "pytest"}
_GIT_READ_ONLY = {"status", "diff", "show", "log", "branch"}
_BLOCKED = {"rm", "mv", "cp", "chmod", "chown", "curl", "wget", "pip", "npm", "yarn", "git", "docker"}
_BLOCKED_GIT = {"commit", "push", "pull", "restore", "checkout", "switch", "merge", "rebase", "reset", "clean"}
_WRITE_MARKERS = (">", ">>", "|", "&&", ";")


@dataclass(slots=True, frozen=True)
class SimplePolicyEngine(PolicyEngine):
    def evaluate_command(self, command: str) -> PolicyDecision:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return PolicyDecision(
                action=PolicyAction.DENY,
                risk_level=RiskLevel.WORKSPACE_WRITE,
                reason=f"Command parsing failed: {exc}",
            )
        if not parts:
            return PolicyDecision(action=PolicyAction.DENY, risk_level=RiskLevel.READ_ONLY, reason="Empty command.")
        if any(marker in command for marker in _WRITE_MARKERS):
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                risk_level=RiskLevel.WORKSPACE_WRITE,
                reason="Shell chaining/redirection is blocked in Phase 5 baseline.",
                safer_alternative="Run a single read-only command without pipes or redirection.",
            )
        first = parts[0]
        if first in {"python", "python3", ".venv/bin/python", "./.venv/bin/python"}:
            return self._python_policy(parts)
        if first == "git":
            subcommand = parts[1] if len(parts) > 1 else ""
            if subcommand in _GIT_READ_ONLY:
                return PolicyDecision(action=PolicyAction.ALLOW, risk_level=RiskLevel.READ_ONLY, reason="Read-only git command.")
            if subcommand in _BLOCKED_GIT:
                return PolicyDecision(
                    action=PolicyAction.REQUIRE_APPROVAL,
                    risk_level=RiskLevel.WORKSPACE_WRITE,
                    reason=f"Git subcommand '{subcommand}' mutates repository state.",
                    safer_alternative="Use git status/diff/show/log/branch for inspection.",
                )
        if first in _READ_ONLY:
            return PolicyDecision(action=PolicyAction.ALLOW, risk_level=RiskLevel.READ_ONLY, reason="Read-only command.")
        if first in _BLOCKED:
            return PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                risk_level=RiskLevel.WORKSPACE_WRITE,
                reason=f"Command '{first}' can change workspace or external state.",
                safer_alternative="Inspect files first with rg/cat/git diff before mutating anything.",
            )
        return PolicyDecision(
            action=PolicyAction.REQUIRE_APPROVAL,
            risk_level=RiskLevel.WORKSPACE_WRITE,
            reason="Unknown command is not allowed in Phase 5 baseline.",
            safer_alternative="Use a supported read-only command or extend the policy layer intentionally.",
        )

    async def evaluate_tool_call(self, command: str) -> PolicyDecision:
        return self.evaluate_command(command)

    def _python_policy(self, parts: list[str]) -> PolicyDecision:
        normalized = tuple(parts[1:4])
        if normalized[:2] == ("-m", "unittest") or normalized[:2] == ("-m", "pytest"):
            return PolicyDecision(action=PolicyAction.ALLOW, risk_level=RiskLevel.READ_ONLY, reason="Test command allowed.")
        return PolicyDecision(
            action=PolicyAction.REQUIRE_APPROVAL,
            risk_level=RiskLevel.WORKSPACE_WRITE,
            reason="Arbitrary Python execution can mutate workspace state.",
            safer_alternative="Use python -m unittest or python -m pytest for verification.",
        )
