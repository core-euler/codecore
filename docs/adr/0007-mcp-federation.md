# ADR 0007: MCP Federation with Trust Profiles

## Status
Accepted

## Date
2026-03-22

## Context

MCP стал стандартным способом подключать инструменты, resources и prompts к LLM-приложениям. Для CodeCore это важно, но слепое подключение множества серверов создаёт новую проблему: шумные schema definitions, рост attack surface и слабый governance.

## Decision

CodeCore интегрирует MCP как capability federation layer, но не как единственный механизм инструментов.

Правила:

- MCP используется для внешних, reusable и discovery-friendly интеграций;
- локальные и детерминированные dev operations могут выполняться через CLI/tool adapters без MCP-обёртки;
- каждый MCP server имеет trust profile;
- capabilities активируются динамически, а не держатся в полном объёме всегда в контексте.

Trust profile обязан хранить:

- transport;
- auth mode;
- risk class;
- side-effect profile;
- data sensitivity;
- reliability history;
- usefulness by task type.

Runtime обязан уметь:

- discover servers;
- rank them;
- selectively enable/disable;
- log usage and outcome;
- блокировать untrusted/high-risk actions через policy engine.

## Consequences

Плюсы:

- MCP становится управляемой частью платформы, а не зоопарком инструментов;
- можно объединять tools/resources/prompts разных серверов под единым governance;
- уменьшается шум от лишних capabilities;
- повышается безопасность и explainability.

Минусы:

- добавляется ещё один слой runtime coordination;
- нужно поддерживать metadata и trust scoring;
- не все задачи стоит вести через MCP, что требует осознанного tool strategy.

Принятый компромисс:

- CodeCore будет `MCP-native`, но не `MCP-only`.
