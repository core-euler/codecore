"""Runtime state container."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RuntimeState:
    active_provider: str | None = None
    active_model: str | None = None
    active_pipeline: str | None = None
    manual_model_alias: str | None = None
    active_skills: list[str] = field(default_factory=list)
    active_files: list[str] = field(default_factory=list)

    @classmethod
    def default(cls) -> "RuntimeState":
        return cls()
