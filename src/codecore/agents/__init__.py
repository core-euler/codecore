"""Multi-agent orchestration primitives."""

from .classifier import TaskClassifier
from .coder import AUTOEDIT_SYSTEM_PROMPT, CoderAgent
from .evaluator import EvaluatorAgent
from .models import (
    AgentRole,
    BenchmarkResult,
    ClassifiedTask,
    CoderOutput,
    EvaluationOutput,
    PipelineDefinition,
    PlannerOutput,
    PlanStep,
    ReviewFinding,
    ReviewOutput,
    WorkflowResult,
)
from .pipelines import DEFAULT_PIPELINES, PipelineRegistry
from .planner import PlannerAgent
from .reviewer import ReviewerAgent
from .runner import MultiAgentRunner
from .synthesizer import SynthesizerAgent

__all__ = [
    "AUTOEDIT_SYSTEM_PROMPT",
    "AgentRole",
    "BenchmarkResult",
    "ClassifiedTask",
    "CoderAgent",
    "CoderOutput",
    "DEFAULT_PIPELINES",
    "EvaluationOutput",
    "EvaluatorAgent",
    "MultiAgentRunner",
    "PipelineDefinition",
    "PipelineRegistry",
    "PlanStep",
    "PlannerAgent",
    "PlannerOutput",
    "ReviewFinding",
    "ReviewOutput",
    "ReviewerAgent",
    "SynthesizerAgent",
    "TaskClassifier",
    "WorkflowResult",
]
