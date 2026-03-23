"""Heuristic task classification for pipeline selection."""

from __future__ import annotations

from ..domain.enums import TaskTag
from .models import ClassifiedTask

_COMPLEX_MARKERS = ("plan", "architecture", "refactor", "complex", "multi", "review", "pipeline")


class TaskClassifier:
    def classify(self, instruction: str, *, task_tag: TaskTag, active_files: tuple[str, ...]) -> ClassifiedTask:
        lowered = instruction.lower()
        if task_tag == TaskTag.REVIEW or "review" in lowered:
            return ClassifiedTask(
                pipeline_id="planner-coder-reviewer",
                reason="Review-oriented task benefits from explicit planning and review.",
                complexity="complex",
            )
        if len(active_files) >= 3 or any(marker in lowered for marker in _COMPLEX_MARKERS):
            return ClassifiedTask(
                pipeline_id="planner-coder-reviewer",
                reason="Task spans multiple files or indicates higher coordination cost.",
                complexity="complex",
            )
        if len(active_files) >= 2:
            return ClassifiedTask(
                pipeline_id="planner-coder",
                reason="Task touches more than one file and benefits from a lightweight plan.",
                complexity="medium",
            )
        return ClassifiedTask(
            pipeline_id="coder-only",
            reason="Single-file task can go through the shortest effective pipeline.",
            complexity="simple",
        )
