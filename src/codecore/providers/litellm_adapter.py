"""LiteLLM-backed adapter for OpenAI-compatible providers."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from time import perf_counter

from litellm import acompletion

from ..domain.enums import HealthState
from ..domain.models import ChatRequest, ChatResult, HealthStatus, ProviderRoute
from .capabilities import route_capabilities
from .pricing import estimate_cost


class LiteLLMAdapter:
    def __init__(self, route: ProviderRoute) -> None:
        self._route = route

    def _resolve_litellm_model(self) -> str:
        model_id = self._route.model_id.strip()
        if "/" in model_id:
            return model_id
        provider = self._route.provider_id.strip()
        if not provider:
            return model_id
        return f"{provider}/{model_id}"

    def _resolve_api_key(self) -> str | None:
        auth = self._route.auth_strategy
        if not auth:
            return None
        if auth.startswith("env:"):
            return os.getenv(auth.removeprefix("env:"))
        return None

    async def chat(self, request: ChatRequest) -> ChatResult:
        api_key = self._resolve_api_key()
        if not api_key:
            raise RuntimeError(f"Missing API key for route {self._route.provider_id}:{self._route.model_id}")

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend({"role": msg.role, "content": msg.content} for msg in request.messages)

        started = perf_counter()
        response = await acompletion(
            model=self._resolve_litellm_model(),
            messages=messages,
            api_base=self._route.base_url,
            api_key=api_key,
        )
        latency_ms = int((perf_counter() - started) * 1000)

        choice = response.choices[0]
        text = choice.message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None)
        output_tokens = getattr(usage, "completion_tokens", None)
        return ChatResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=estimate_cost(self._route, input_tokens, output_tokens),
            finish_reason=getattr(choice, "finish_reason", None),
            metadata={"provider_id": self._route.provider_id},
        )

    async def stream(self, request: ChatRequest):
        result = await self.chat(request)
        yield result.text

    async def health(self) -> HealthStatus:
        api_key = self._resolve_api_key()
        if not api_key:
            return HealthStatus(
                state=HealthState.UNAVAILABLE,
                checked_at=datetime.now(timezone.utc),
                detail="missing API key",
            )
        return HealthStatus(
            state=HealthState.HEALTHY,
            checked_at=datetime.now(timezone.utc),
            detail="API key available",
        )

    def capabilities(self):
        return route_capabilities(self._route)
