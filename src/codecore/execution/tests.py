"""Verification helpers for running tests and summarizing failures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..domain.contracts import ToolExecutor, VerificationEngine
from ..domain.results import VerificationResult
from .shell import summarize_output


@dataclass(slots=True, frozen=True)
class VerificationPlan:
    command: str
    source: str


class VerificationPlanner:
    def build_default(self, project_root: Path) -> VerificationPlan | None:
        if (project_root / "tests").exists():
            python_bin = project_root / ".venv" / "bin" / "python"
            if python_bin.exists():
                return VerificationPlan(command="./.venv/bin/python -m unittest discover -s tests -v", source="default:test-suite")
            return VerificationPlan(command="python3 -m unittest discover -s tests -v", source="default:test-suite")
        return None


class VerificationRunner(VerificationEngine):
    def __init__(self, tool_executor: ToolExecutor, project_root: Path, planner: VerificationPlanner | None = None) -> None:
        self._tool_executor = tool_executor
        self._project_root = project_root
        self._planner = planner or VerificationPlanner()

    async def verify(self, command: str | None = None) -> VerificationResult:
        plan = VerificationPlan(command=command, source="explicit") if command else self._planner.build_default(self._project_root)
        if plan is None:
            return VerificationResult(passed=False, summary="No verification command is configured.")
        result = await self._tool_executor.run_shell(plan.command, cwd=self._project_root)
        passed = result.exit_code == 0
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        summary = summarize_output(combined or "<no output>", max_chars=1600).rendered
        failures: tuple[str, ...] = ()
        if not passed and summary:
            failures = tuple(line for line in summary.splitlines()[:8] if line.strip())
        return VerificationResult(
            passed=passed,
            summary=summary,
            checks_run=(plan.command,),
            failures=failures,
            metadata={"source": plan.source, **result.metadata},
        )
