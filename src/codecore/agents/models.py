"""Domain models for multi-agent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..execution.changesets import ChangeSet


class AgentRole(str, Enum):
    CLASSIFIER = "classifier"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    EVALUATOR = "evaluator"
    SYNTHESIZER = "synthesizer"


@dataclass(slots=True, frozen=True)
class PipelineDefinition:
    pipeline_id: str
    roles: tuple[AgentRole, ...]
    isolated_roles: tuple[AgentRole, ...] = ()
    description: str = ""


@dataclass(slots=True, frozen=True)
class ClassifiedTask:
    pipeline_id: str
    reason: str
    complexity: str


@dataclass(slots=True, frozen=True)
class PlanStep:
    title: str
    detail: str = ""


@dataclass(slots=True, frozen=True)
class PlannerOutput:
    summary: str
    steps: tuple[PlanStep, ...]


@dataclass(slots=True, frozen=True)
class CoderOutput:
    applied_files: tuple[str, ...]
    edit_count: int
    diff_summary: str
    workspace_path: str
    isolated: bool


@dataclass(slots=True, frozen=True)
class ReviewFinding:
    severity: str
    message: str


@dataclass(slots=True, frozen=True)
class ReviewOutput:
    approved: bool
    summary: str
    findings: tuple[ReviewFinding, ...] = ()


@dataclass(slots=True, frozen=True)
class EvaluationOutput:
    status: str
    summary: str
    checks_run: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class BenchmarkResult:
    model_alias: str
    pipeline_id: str
    success: bool
    evaluation_status: str = "skipped"
    review_status: str = "skipped"
    retry_count: int = 0
    edit_count: int = 0
    summary: str = ""
    error: str = ""


@dataclass(slots=True, frozen=True)
class WorkflowResult:
    pipeline_id: str
    classification: ClassifiedTask
    plan: PlannerOutput
    coding: CoderOutput
    review: ReviewOutput | None = None
    evaluation: EvaluationOutput | None = None
    workspace_path: str | None = None
    review_workspace_path: str | None = None
    isolated: bool = False
    retry_count: int = 0
    merge_ready: bool = False
    change_set: ChangeSet | None = None
    summary: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
