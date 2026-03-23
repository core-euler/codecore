# ADR 0005: Provider Fabric and Policy-Driven Broker

## Status
Accepted

## Date
2026-03-22

## Context

CodeCore должен работать с облачными API, локальными моделями, OpenAI-compatible gateways и mixed pipelines. Ручное переключение между провайдерами не масштабируется и не решает проблему блокировок, стоимости, latency и VPN-зависимости.

## Decision

Подключение моделей строится через `provider fabric`:

- каждый провайдер описывается manifest'ом;
- каждый manifest реализуется adapter'ом, совместимым с `ModelGateway`;
- broker выбирает не “любимую модель”, а лучший маршрут под конкретную задачу.

Broker обязан учитывать:

- capability fit;
- context capacity;
- tool/json/vision support;
- latency;
- cost;
- availability;
- geo and VPN constraints;
- privacy policy;
- historical reliability;
- outcome rankings by task type.

Runtime обязан поддерживать:

- fallback chain;
- degraded mode;
- hybrid routing;
- cached health decisions.

Hybrid routing допускает разные модели для ролей:

- planner;
- coder;
- reviewer;
- evaluator.

## Consequences

Плюсы:

- система становится реально provider-agnostic;
- можно балансировать цену, качество и доступность;
- появляется устойчивость к лимитам и отказам;
- легче подключать локальные модели и self-hosted gateways.

Минусы:

- broker сложнее, чем статический `--model`;
- нужна поддержка health checks и capability metadata;
- возрастает число маршрутов, которые надо измерять.

Принятый компромисс:

- в MVP broker может начинаться с простых правил и fallback;
- но manifest-driven fabric вводится сразу как несущий принцип.
