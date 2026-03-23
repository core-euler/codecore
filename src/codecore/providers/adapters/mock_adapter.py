"""Mock model adapter for offline and test flows."""

from __future__ import annotations

from datetime import datetime, timezone

from ...domain.models import ChatRequest, ChatResult, HealthStatus, ProviderRoute
from ...domain.enums import HealthState
from ..capabilities import route_capabilities
from ..pricing import estimate_cost


class MockModelAdapter:
    def __init__(self, route: ProviderRoute) -> None:
        self._route = route

    async def chat(self, request: ChatRequest) -> ChatResult:
        prompt = request.messages[-1].content if request.messages else ""
        text = f"[mock:{self._route.alias or self._route.model_id}] {prompt}"
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(text) // 4)
        return ChatResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=5,
            cost_usd=estimate_cost(self._route, input_tokens, output_tokens),
            finish_reason="stop",
            metadata={"mock": True},
        )

    async def stream(self, request: ChatRequest):
        yield (await self.chat(request)).text

    async def health(self) -> HealthStatus:
        return HealthStatus(
            state=HealthState.HEALTHY,
            checked_at=datetime.now(timezone.utc),
            latency_ms=1,
            detail="mock provider always available",
        )

    def capabilities(self):
        return route_capabilities(self._route)
