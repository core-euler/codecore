"""Slash-command routing for the REPL."""

from __future__ import annotations

import shlex
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

CommandHandler = Callable[[list[str]], Awaitable["CommandResult"]]


@dataclass(slots=True, frozen=True)
class CommandResult:
    output: str = ""
    should_exit: bool = False
    is_error: bool = False
    render_mode: str = "text"


class CommandRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, name: str, handler: CommandHandler) -> None:
        self._handlers[name] = handler

    async def dispatch(self, line: str) -> CommandResult:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            return CommandResult(output=f"Command parse error: {exc}", is_error=True)
        if not parts:
            return CommandResult()

        command = parts[0].removeprefix("/")
        handler = self._handlers.get(command)
        if handler is None:
            return CommandResult(output=f"Unknown command: /{command}", is_error=True)
        return await handler(parts[1:])
