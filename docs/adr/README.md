# CodeCore ADR Index

Этот каталог хранит `Architecture Decision Records` — короткие документы, фиксирующие несущие архитектурные решения проекта.

## Формат ADR

Каждый ADR должен содержать:

- `Title`
- `Status`
- `Date`
- `Context`
- `Decision`
- `Consequences`

Допустимые статусы:

- `Proposed`
- `Accepted`
- `Superseded`
- `Deprecated`

## Правила

- Один ADR = одно архитектурное решение.
- ADR фиксирует не обсуждение, а принятое решение и его последствия.
- ADR пишется тогда, когда решение влияет на кодовую базу, runtime, данные, операционную модель или безопасность.
- Изменение несущего решения делается новым ADR, а не незаметной правкой старого.

## Индекс

- `0001` — Hexagonal Runtime and Ports
- `0002` — Event-Sourced Runtime Model
- `0003` — Memory Taxonomy and Selective Recall
- `0004` — LLM as Engine, Environment as System
- `0005` — Provider Fabric and Policy-Driven Broker
- `0006` — Context Engineering and Progressive Skill Loading
- `0007` — MCP Federation with Trust Profiles
- `0008` — Verification, Policy Gates, and Audit Trail
- `0009` — Parallel Agents via Isolated Execution Contexts
- `0010` — Spec-Driven Delivery Workflow
