"""Results returned by execution, policy, and verification layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import PolicyAction, RiskLevel, ToolKind


@dataclass(slots=True, frozen=True)
class ToolExecutionResult:
    tool_kind: ToolKind
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int | None = None
    affected_files: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PolicyDecision:
    action: PolicyAction
    risk_level: RiskLevel
    reason: str = ""
    safer_alternative: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class VerificationResult:
    passed: bool
    summary: str
    checks_run: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
