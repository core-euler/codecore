# ADR 0010: Spec-Driven Delivery Workflow

## Status
Accepted

## Date
2026-03-22

## Context

LLM ускоряют генерацию кода, но вместе с этим усиливают архитектурный шум. Если разработка строится как серия неструктурированных запросов, проект быстро теряет управляемость. Для CodeCore, который должен быть домом для агентной инженерии, нужен встроенный рабочий цикл, а не набор разрозненных команд.

## Decision

CodeCore принимает spec-driven workflow как основной маршрут для нетривиальных задач:

`idea -> spec -> plan -> tasks -> implementation -> verification`

Система должна поддерживать как first-class artifacts:

- spec;
- implementation plan;
- task decomposition;
- verification evidence;
- handoff summary.

Практические правила:

- крупные задачи не начинают напрямую с file editing;
- у каждой нетривиальной задачи должны быть explicit constraints и non-goals;
- pipeline вправе требовать plan phase до execute phase;
- финальный outcome соотносится с acceptance criteria, а не с субъективным ощущением модели.

## Consequences

Плюсы:

- уменьшается vibe-driven chaos;
- проще ревьюить и повторять работу;
- агенты получают устойчивый artifact of intention;
- acceptance criteria становятся частью runtime, а не только головы оператора.

Минусы:

- для мелких задач добавляется overhead, если применять SDD без разбора;
- нужна классификация, когда задача достаточно сложна для spec-first режима;
- появляются дополнительные документы и состояния workflow.

Принятый компромисс:

- для маленьких задач допускается сокращённый путь;
- для архитектурных, многошаговых и рискованных изменений spec-driven delivery обязателен.
