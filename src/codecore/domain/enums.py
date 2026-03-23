"""Core enums shared across the runtime."""

from __future__ import annotations

from enum import Enum


class TaskTag(str, Enum):
    GENERAL = "general"
    CODE = "code"
    REFACTOR = "refactor"
    DEBUG = "debug"
    REVIEW = "review"
    ARCH = "arch"
    RUN = "run"


class EventKind(str, Enum):
    SESSION_STARTED = "session.started"
    TASK_CLASSIFIED = "task.classified"
    PIPELINE_SELECTED = "pipeline.selected"
    PROVIDER_SELECTED = "provider.selected"
    MODEL_INVOKED = "model.invoked"
    SKILL_ACTIVATED = "skill.activated"
    TOOL_CALLED = "tool.called"
    TOOL_FINISHED = "tool.finished"
    PATCH_PROPOSED = "patch.proposed"
    PATCH_APPLIED = "patch.applied"
    VERIFICATION_FINISHED = "verification.finished"
    POLICY_BLOCKED = "policy.blocked"
    FALLBACK_TRIGGERED = "fallback.triggered"
    SESSION_FINISHED = "session.finished"
    FEEDBACK_RECORDED = "feedback.recorded"


class MemoryScope(str, Enum):
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"
    OUTCOME = "outcome"
    GOVERNANCE = "governance"


class RuntimeMode(str, Enum):
    INTERACTIVE = "interactive"
    BATCH = "batch"
    HEADLESS = "headless"


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    DESTRUCTIVE = "destructive"
    NETWORKED = "networked"
    SECRET_TOUCHING = "secret_touching"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


class PolicyAction(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    DOWNGRADE = "downgrade"
    SAFER_ALTERNATIVE = "safer_alternative"


class ToolKind(str, Enum):
    SHELL = "shell"
    FILESYSTEM = "filesystem"
    PATCH = "patch"
    GIT = "git"
    MCP = "mcp"


class HealthState(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
