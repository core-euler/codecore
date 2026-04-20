"""Interactive first-run LLM setup."""

from __future__ import annotations

import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import radiolist_dialog
from rich.console import Console

from ..infra.llm_setup import LLMSetupService


async def ensure_llm_ready(console: Console, service: LLMSetupService) -> bool:
    if await service.is_ready():
        preferred = service.preferred_alias()
        if preferred and not service.runtime_state.manual_model_alias:
            service.runtime_state.manual_model_alias = preferred
        return True
    if not sys.stdin.isatty():
        console.print(
            "No LLM is configured. Start CodeCore in an interactive terminal and connect a provider first.",
            style="red",
        )
        return False
    return await _run_interactive_setup(console, service)


async def _run_interactive_setup(console: Console, service: LLMSetupService) -> bool:
    choices = service.setup_choices()
    if not choices:
        console.print("No API-backed providers are configured in the provider registry.", style="red")
        return False

    console.print()
    console.print("CodeCore requires a real LLM before the session can start.", style="bold yellow")
    console.print("Select a model, enter its API key, and CodeCore will save it to `.codecore/auth.env`.", style="dim")

    preferred = service.preferred_alias()
    selected_alias = await radiolist_dialog(
        title="Connect LLM",
        text="Choose the default model for this project:",
        values=[(choice.alias, f"{choice.label}  [{choice.env_name}]") for choice in choices],
        default=preferred or choices[0].alias,
    ).run_async()
    if selected_alias is None:
        console.print("LLM setup was cancelled.", style="red")
        return False

    selected = service.resolve_choice(selected_alias)
    if selected is None:
        console.print(f"Unknown model alias: {selected_alias}", style="red")
        return False

    prompt = PromptSession()
    try:
        api_key = await prompt.prompt_async(f"{selected.env_name}: ", is_password=True)
    except (EOFError, KeyboardInterrupt):
        console.print("\nLLM setup was cancelled.", style="red")
        return False
    if not api_key.strip():
        console.print("API key is required.", style="red")
        return False

    service.save(alias=selected.alias, api_key=api_key)
    if not await service.is_ready():
        console.print("The provider is still unavailable after saving the key.", style="red")
        return False

    console.print(f"Connected {selected.label}. Starting session.", style="green")
    return True
