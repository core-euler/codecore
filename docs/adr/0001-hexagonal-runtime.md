# ADR 0001: Hexagonal Runtime and Ports

## Status
Accepted

## Date
2026-03-22

## Context

CodeCore должен одновременно работать с разными моделями, локальными и облачными runtime, CLI-инструментами, MCP-серверами, памятью, политиками и несколькими интерфейсами. Если ядро будет напрямую зависеть от провайдеров, SQLite, shell execution или конкретного UI, система быстро потеряет расширяемость и управляемость.

Для проекта с self-improving логикой это критично: ядро должно координировать сессию, а не знать детали каждого внешнего механизма.

## Decision

CodeCore строится по hexagonal architecture.

Внутри ядра допускаются только доменные сущности и порты. Внешние детали подключаются адаптерами.

Обязательные порты:

- `ModelGateway`
- `ProviderBroker`
- `ContextComposer`
- `SkillRegistry`
- `MemoryStore`
- `TelemetrySink`
- `ToolExecutor`
- `PolicyEngine`
- `ArtifactStore`

Структурное правило:

- `domain/` и `kernel/` не импортируют `providers/`, `execution/`, `infra/`, `ui/`;
- `bootstrap.py` собирает runtime-композицию;
- провайдеры, MCP, shell, SQLite, REPL, файлы и network живут только в адаптерах.

Kernel отвечает за:

- lifecycle сессии;
- orchestration turn-by-turn;
- выбор pipeline;
- публикацию событий;
- применение policy decisions;
- передачу команд в зависимости через порты.

## Consequences

Плюсы:

- можно менять провайдеров, transport, storage и UI без переписывания ядра;
- проще тестировать orchestration через mock adapters;
- легче вводить локальный режим, headless режим и будущий API server;
- архитектура естественно поддерживает skills, MCP и policy engine как независимые подсистемы.

Минусы:

- выше стартовая сложность проекта;
- требуется дисциплина импортов и явные интерфейсы;
- часть логики, которую удобно “быстро написать прямо в REPL-слое”, придётся держать вне UI.

Принятый компромисс:

- допускается более медрый старт реализации;
- не допускается протаскивание infra-зависимостей в kernel ради скорости MVP.
