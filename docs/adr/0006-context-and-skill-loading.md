# ADR 0006: Context Engineering and Progressive Skill Loading

## Status
Accepted

## Date
2026-03-22

## Context

Главный ограничитель агентных систем - не столько размер окна, сколько шум в контексте. Если держать в prompt все правила, всю историю, все логи и весь объём знаний, качество и экономика быстро деградируют.

CodeCore должен проектироваться вокруг управляемого контекстного бюджета.

## Decision

Context engineering становится first-class подсистемой.

Основные правила:

- контекст собирается из минимально достаточных артефактов;
- большие tool outputs сохраняются как artifacts, а в prompt попадает summary-first представление;
- stale context удаляется или заменяется delta-updates;
- `clear` и `compact` - разные операции;
- для длинных задач создаются persistent handoff artifacts.

Skills загружаются через progressive disclosure:

1. metadata всегда доступны;
2. полные инструкции загружаются только при релевантности;
3. scripts, templates и references читаются on demand.

Skills являются workflow packages, а не набором случайных markdown-файлов.

Минимальный skill contract:

- manifest;
- activation triggers;
- workflow steps;
- constraints;
- stop conditions;
- optional resources.

## Consequences

Плюсы:

- уменьшается fixed context overhead;
- база skills может расти без загрязнения сессий;
- long-running tasks становятся устойчивее;
- система лучше переживает смену модели и context limits.

Минусы:

- требуется отдельная логика relevance, compaction и artifact retention;
- часть ошибок будет происходить из-за неверного контекстного отбора, а не из-за самой модели;
- skill ecosystem требует дисциплины метаданных.

Принятый компромисс:

- сначала вводится строгая summary-first и progressive loading модель;
- richer relevance heuristics и semantic retrieval расширяются позже.
