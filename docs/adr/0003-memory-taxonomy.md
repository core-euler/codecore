# ADR 0003: Memory Taxonomy and Selective Recall

## Status
Accepted

## Date
2026-03-22

## Context

Для CodeCore память - ключевой механизм эволюции. Однако “память как вся история чата” быстро превращается в шум, дорогой контекст и бесполезный архив. Нужна система, которая сохраняет только то, что усиливает будущую разработку.

## Decision

Память CodeCore делится на пять уровней:

- `session memory` — временное состояние текущей задачи;
- `project memory` — правила, решения и паттерны конкретного репозитория;
- `global memory` — кросс-проектные практики и рейтинги;
- `outcome memory` — что сработало/не сработало и при каких условиях;
- `governance memory` — ограничения, риски, плохие маршруты, trust history.

В память не записывается весь transcript по умолчанию.

В память записываются только:

- decisions;
- constraints;
- verified facts;
- reusable workflows;
- failure signatures;
- model/skill/tool outcomes;
- handoff summaries.

Каждая memory unit обязана иметь metadata envelope:

- origin;
- task tag;
- project id;
- provider/model;
- skill ids;
- tool ids;
- freshness;
- confidence/trust;
- quality score.

Recall строится по принципу selective retrieval:

- сначала project- и session-relevant knowledge;
- затем outcome patterns;
- затем global memory;
- governance memory может понижать или блокировать маршрут.

Vector search не является стартовым требованием.

## Consequences

Плюсы:

- память становится управляемой и полезной;
- можно строить ranking и recall без загрязнения контекста;
- появляется основа для будущего memory learning;
- снижается соблазн хранить всё подряд.

Минусы:

- требуется явная логика write/reject для memory units;
- часть полезных данных можно поначалу не сохранять из-за строгой селекции;
- recall сложнее, чем “просто подмешать историю”.

Принятый компромисс:

- сначала metadata-first memory и summaries;
- vector and graph expansion — только при реальной необходимости.
