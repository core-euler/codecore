"""Asynchronous event publication."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.contracts import TelemetrySink
from ..domain.events import EventEnvelope


@dataclass(slots=True)
class EventBus:
    sinks: list[TelemetrySink] = field(default_factory=list)

    async def publish(self, event: EventEnvelope) -> None:
        for sink in self.sinks:
            await sink.publish(event)
