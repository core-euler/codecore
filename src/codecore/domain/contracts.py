"""Port definitions for the hexagonal runtime."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator, Protocol

from .events import EventEnvelope
from .models import (
    ArtifactRef,
    ChatRequest,
    ChatResult,
    HealthStatus,
    MemoryRecord,
    ModelCapabilities,
    ProviderRoute,
    SkillDescriptor,
)
from .results import PolicyDecision, ToolExecutionResult, VerificationResult


class ModelGateway(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResult:
        """Execute a non-streaming chat request."""

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream chat output chunks."""

    async def health(self) -> HealthStatus:
        """Return current provider health status."""

    def capabilities(self) -> ModelCapabilities:
        """Return static capability metadata for the model endpoint."""


class ProviderBroker(Protocol):
    async def select_route(self, request: ChatRequest) -> ProviderRoute:
        """Choose the best model route for the current task."""


class ContextComposer(Protocol):
    async def compose(self, request: ChatRequest) -> ChatRequest:
        """Return a prompt-ready request with attached context."""


class SkillRegistry(Protocol):
    async def list_skills(self) -> tuple[SkillDescriptor, ...]:
        """List known skill descriptors."""

    async def resolve(self, skill_id: str) -> SkillDescriptor:
        """Resolve a single skill descriptor by identifier."""


class MemoryStore(Protocol):
    async def write(self, record: MemoryRecord) -> None:
        """Persist a memory unit."""

    async def recall(self, *, query: str, limit: int = 10) -> tuple[MemoryRecord, ...]:
        """Return relevant memory units for a query."""


class TelemetrySink(Protocol):
    async def publish(self, event: EventEnvelope) -> None:
        """Persist or forward a runtime event."""


class ToolExecutor(Protocol):
    async def run_shell(self, command: str, *, cwd: Path | None = None) -> ToolExecutionResult:
        """Execute a shell command within the active sandbox."""


class PolicyEngine(Protocol):
    async def evaluate_tool_call(self, command: str) -> PolicyDecision:
        """Evaluate whether the requested tool action is allowed."""


class ArtifactStore(Protocol):
    async def save_text(self, *, kind: str, name: str, content: str) -> ArtifactRef:
        """Save text as a named artifact and return a stable reference."""


class VerificationEngine(Protocol):
    async def verify(self, command: str | None = None) -> VerificationResult:
        """Run the active verification pipeline."""
