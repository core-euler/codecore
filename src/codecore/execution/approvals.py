"""Explicit approval requests for risky execution steps."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..domain.enums import RiskLevel


@dataclass(slots=True, frozen=True)
class ApprovalRequest:
    approval_id: str
    action: str
    command: str
    risk_level: RiskLevel
    reason: str
    safer_alternative: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalManager:
    def __init__(self) -> None:
        self._pending: dict[str, ApprovalRequest] = {}

    def create(
        self,
        *,
        action: str,
        command: str,
        risk_level: RiskLevel,
        reason: str,
        safer_alternative: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=str(uuid4())[:8],
            action=action,
            command=command,
            risk_level=risk_level,
            reason=reason,
            safer_alternative=safer_alternative,
            metadata=dict(metadata or {}),
        )
        self._pending[request.approval_id] = request
        return request

    def resolve(self, approval_id: str) -> ApprovalRequest | None:
        return self._pending.pop(approval_id, None)

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._pending.get(approval_id)

    def list_pending(self) -> tuple[ApprovalRequest, ...]:
        return tuple(sorted(self._pending.values(), key=lambda item: item.created_at))
