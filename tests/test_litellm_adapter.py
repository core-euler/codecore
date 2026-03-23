from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from codecore.domain.models import ChatMessage, ChatRequest, ProviderRoute
from codecore.providers.litellm_adapter import LiteLLMAdapter


class _FakeUsage:
    prompt_tokens = 7
    completion_tokens = 5


class _FakeMessage:
    content = "hello"


class _FakeChoice:
    message = _FakeMessage()
    finish_reason = "stop"


class _FakeResponse:
    choices = [_FakeChoice()]
    usage = _FakeUsage()


class LiteLLMAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "test-key"

    async def asyncTearDown(self) -> None:
        os.environ.pop("DEEPSEEK_API_KEY", None)

    async def test_chat_prefixes_provider_for_plain_model_id(self) -> None:
        route = ProviderRoute(
            provider_id="deepseek",
            model_id="deepseek-chat",
            alias="ds-v3",
            base_url="https://api.deepseek.com",
            auth_strategy="env:DEEPSEEK_API_KEY",
        )
        adapter = LiteLLMAdapter(route)
        request = ChatRequest(messages=(ChatMessage(role="user", content="hi"),))

        with patch("codecore.providers.litellm_adapter.acompletion", return_value=_FakeResponse()) as mocked:
            result = await adapter.chat(request)

        self.assertEqual(result.text, "hello")
        self.assertEqual(mocked.call_args.kwargs["model"], "deepseek/deepseek-chat")

    async def test_chat_keeps_prefixed_model_id_unchanged(self) -> None:
        route = ProviderRoute(
            provider_id="openrouter",
            model_id="anthropic/claude-sonnet-4-5",
            alias="claude",
            base_url="https://openrouter.ai/api/v1",
            auth_strategy="env:DEEPSEEK_API_KEY",
        )
        adapter = LiteLLMAdapter(route)
        request = ChatRequest(messages=(ChatMessage(role="user", content="hi"),))

        with patch("codecore.providers.litellm_adapter.acompletion", return_value=_FakeResponse()) as mocked:
            await adapter.chat(request)

        self.assertEqual(mocked.call_args.kwargs["model"], "anthropic/claude-sonnet-4-5")

    async def test_chat_raises_when_api_key_missing(self) -> None:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        route = ProviderRoute(
            provider_id="deepseek",
            model_id="deepseek-chat",
            base_url="https://api.deepseek.com",
            auth_strategy="env:DEEPSEEK_API_KEY",
        )
        adapter = LiteLLMAdapter(route)
        request = ChatRequest(messages=(ChatMessage(role="user", content="hi"),))

        with self.assertRaises(RuntimeError):
            await adapter.chat(request)


if __name__ == "__main__":
    unittest.main()
