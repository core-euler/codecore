---
name: telegram
description: Build Telegram-oriented bots and integrations with attention to update flow, state, and rate limits.
version: "1"
summary: Use when the task involves Telegram bots, commands, webhook updates, or chat workflows.
tags: [telegram, bot]
triggers: [telegram, bot, webhook, chat, callback query, inline keyboard, update]
constraints:
  - Preserve deterministic update handling.
  - Keep chat state transitions explicit.
stop_conditions:
  - Update flow, state behavior, and failure handling are specified.
---

# Telegram Skill

1. Model the update lifecycle before coding handlers.
2. Make user-visible state transitions explicit and recoverable.
3. Validate payloads from callbacks and commands.
4. Respect rate limits and retry behavior for outbound calls.
5. Keep chat-specific logic separate from transport wiring.

Reference files:
- `references/updates.md` for update-flow guardrails.
