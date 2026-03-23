"""Pipeline definitions and lookup helpers."""

from __future__ import annotations

from .models import AgentRole, PipelineDefinition

DEFAULT_PIPELINES: tuple[PipelineDefinition, ...] = (
    PipelineDefinition(
        pipeline_id="coder-only",
        roles=(AgentRole.CODER, AgentRole.EVALUATOR, AgentRole.SYNTHESIZER),
        isolated_roles=(AgentRole.CODER,),
        description="Single coder with isolated execution and evaluation.",
    ),
    PipelineDefinition(
        pipeline_id="planner-coder",
        roles=(AgentRole.PLANNER, AgentRole.CODER, AgentRole.EVALUATOR, AgentRole.SYNTHESIZER),
        isolated_roles=(AgentRole.CODER,),
        description="Planner decomposes the task before isolated coding and evaluation.",
    ),
    PipelineDefinition(
        pipeline_id="planner-coder-reviewer",
        roles=(
            AgentRole.PLANNER,
            AgentRole.CODER,
            AgentRole.REVIEWER,
            AgentRole.EVALUATOR,
            AgentRole.SYNTHESIZER,
        ),
        isolated_roles=(AgentRole.CODER, AgentRole.REVIEWER),
        description="Planner, isolated coder, reviewer, evaluator, and final synthesizer.",
    ),
)


class PipelineRegistry:
    def __init__(self, definitions: tuple[PipelineDefinition, ...] = DEFAULT_PIPELINES) -> None:
        self._definitions = {item.pipeline_id: item for item in definitions}

    def get(self, pipeline_id: str) -> PipelineDefinition:
        try:
            return self._definitions[pipeline_id]
        except KeyError as exc:
            available = ", ".join(sorted(self._definitions))
            raise KeyError(f"Unknown pipeline: {pipeline_id}. Available: {available}") from exc

    def list(self) -> tuple[PipelineDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))
