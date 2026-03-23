# CodeCore Threat Model

## Scope

Этот документ фиксирует базовую threat model для `CodeCore` как локального agent runtime для разработки.

## Assets

- исходный код и рабочее дерево проекта
- локальные секреты: API keys, tokens, `.env`, SSH keys
- telemetry и event logs
- prompts, tool outputs, memory records
- approval history и audit trail

## Trust Boundaries

- `user instruction` — доверенный источник намерения
- `project files` — недоверенный контент
- `tool outputs` — недоверенный контент
- `model outputs` — частично доверенный, но не авторитетный источник
- `provider responses` — внешняя зависимость
- `MCP servers` — внешний расширяемый perimeter

## Primary Threats

1. Prompt injection из файлов, tool output или memory.
2. Утечка секретов в prompts, logs, telemetry, shell output.
3. Неконтролируемая запись в workspace.
4. Silent merge конфликтов при apply-back из isolated contexts.
5. Небезопасные shell/tool calls.
6. Подмена модели или маршрута с деградацией качества и trust.
7. Накопление poisoned memory.

## Current Mitigations

- policy/approval gates для mutating actions
- isolated worktrees для multi-agent execution
- change-set apply-back с exact-content conflict check
- snapshot-backed rollback и git-backed undo
- append-only audit log для file changes
- sanitization и secret redaction в untrusted content / telemetry
- explicit marking of file/tool context as untrusted data
- review/evaluation gates перед merge-ready state

## Residual Risks

- модель всё ещё может сгенерировать unsafe plan в рамках allowed files
- секреты могут существовать в бинарных или нестандартно закодированных файлах
- poisoned memory пока не имеет scoring/quarantine layer
- MCP trust scoring ещё не реализован
- CI security gates и regression policies ещё не подключены

## Next Hardening Steps

1. Secret redaction в audit/memory layers end-to-end.
2. Prompt injection scoring для MCP/resources.
3. Tool allowlists и finer-grained approval classes.
4. Cost/rate guardrails.
5. Regression benchmark suite на реальных задачах.
