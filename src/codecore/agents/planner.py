"""Planning heuristics for multi-agent execution."""

from __future__ import annotations

from .models import PlanStep, PlannerOutput


class PlannerAgent:
    def plan(self, instruction: str, active_files: tuple[str, ...], *, pipeline_id: str) -> PlannerOutput:
        focus = ", ".join(active_files) if active_files else "the active context"
        steps = [
            PlanStep(title="Inspect target scope", detail=f"Validate the change against: {focus}."),
            PlanStep(title="Implement minimal edit set", detail=instruction.strip()),
            PlanStep(title="Verify outcome", detail="Check diff and run the default verification pipeline."),
        ]
        if pipeline_id == "planner-coder-reviewer":
            steps.append(PlanStep(title="Review result", detail="Inspect the diff for regressions and policy risks."))
        return PlannerOutput(
            summary=f"Planned {len(steps)} steps for pipeline `{pipeline_id}`.",
            steps=tuple(steps),
        )
