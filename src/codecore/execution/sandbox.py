"""Sandbox profile metadata for execution commands."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import RiskLevel


@dataclass(slots=True, frozen=True)
class SandboxProfile:
    name: str
    allow_workspace_write: bool
    allow_network: bool
    allow_destructive: bool = False

    @classmethod
    def for_risk(cls, risk_level: RiskLevel, *, approved: bool) -> "SandboxProfile":
        if risk_level == RiskLevel.READ_ONLY:
            return cls(name="read-only", allow_workspace_write=False, allow_network=False)
        if risk_level == RiskLevel.NETWORKED:
            return cls(name="networked", allow_workspace_write=approved, allow_network=True)
        if risk_level == RiskLevel.DESTRUCTIVE:
            return cls(name="destructive", allow_workspace_write=approved, allow_network=False, allow_destructive=approved)
        return cls(name="workspace-write", allow_workspace_write=approved, allow_network=False)
