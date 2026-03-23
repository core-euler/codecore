"""Verification wrapper for multi-agent workflows."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

from ..execution.tests import VerificationRunner
from .models import EvaluationOutput


class EvaluatorAgent:
    def __init__(self, verification_runner_factory: Callable[[Path], VerificationRunner] | None = None) -> None:
        self._factory = verification_runner_factory

    async def evaluate(self, project_root: Path) -> EvaluationOutput:
        runner = self._factory(project_root) if self._factory is not None else None
        if runner is None:
            return EvaluationOutput(status="skipped", summary="Verification runner is not configured.")
        result = await runner.verify(None)
        if result.summary == "No verification command is configured.":
            return EvaluationOutput(status="skipped", summary=result.summary, checks_run=result.checks_run)
        return EvaluationOutput(
            status="passed" if result.passed else "failed",
            summary=result.summary,
            checks_run=result.checks_run,
        )
