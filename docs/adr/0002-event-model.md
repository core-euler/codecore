# ADR 0002: Event-Sourced Runtime Model

## Status
Accepted

## Date
2026-03-22

## Context

CodeCore должен не только отвечать пользователю, но и накапливать инженерный опыт. Для этого недостаточно хранить “последний ответ” или агрегированные метрики. Нужна историчность: как именно был выбран маршрут, какие tools вызывались, что проверялось, где произошёл fallback и чем закончилась задача.

Без событийной модели нельзя надёжно строить:

- self-improving rankings;
- audit trail;
- replay проблемных сессий;
- нормальную аналитику качества.

## Decision

Runtime CodeCore является event-sourced на уровне доменных событий.

Каждое значимое действие оформляется как append-only event.

Минимальный обязательный набор событий:

- `session.started`
- `task.classified`
- `pipeline.selected`
- `provider.selected`
- `model.invoked`
- `skill.activated`
- `context.compacted`
- `tool.called`
- `tool.finished`
- `patch.proposed`
- `patch.applied`
- `verification.finished`
- `policy.blocked`
- `fallback.triggered`
- `session.finished`
- `feedback.recorded`

Стратегия хранения:

- source of truth: append-only JSONL event log;
- query layer: SQLite projections для быстрых выборок и статистики.

Правило проектирования:

- если действие влияет на outcome, стоимость, риск, качество или воспроизводимость, оно должно иметь event.

## Consequences

Плюсы:

- появляется полный audit trail;
- можно строить replay и диагностику неудачных задач;
- rankings и memory получают нормализованный вход;
- проще развивать telemetry без ломки runtime.

Минусы:

- нужна дисциплина схем событий;
- больше инфраструктуры вокруг projection и versioning;
- часть быстрых MVP-решений станет чуть более формальной.

Принятый компромисс:

- на старте схема событий будет компактной;
- но event model вводится сразу, чтобы не мигрировать к ней болезненно позже.
