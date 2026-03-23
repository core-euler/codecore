# CodeCore Roadmap
## Живой roadmap проекта с текущим статусом, этапами и критериями готовности
`updated: 2026-03-23 (phase 7 started: security hardening slice added)`

---

## 1. Как пользоваться этим roadmap

Этот файл - главный рабочий чеклист проекта.

Правила:

- `[x]` — реализовано и зафиксировано в репозитории
- `[ ]` — ещё не реализовано
- задача считается завершённой только если есть соответствующий артефакт: код, тест, конфиг, схема, документ или runnable flow
- документальные задачи считаются завершёнными только для документального слоя, но не для слоя runtime

---

## 2. Текущее состояние проекта

### Уже есть

- [x] Продуктовая концепция: [start.md](./start.md)
- [x] Архитектурный blueprint: [architecture.md](./architecture.md)
- [x] Концентрат лучших практик под CodeCore: [best_practice.md](./best_practice.md)
- [x] ADR-пакет с несущими решениями: [adr/README.md](./adr/README.md)
- [x] Зафиксирован принцип `LLM as engine, environment as system`
- [x] Зафиксирован provider-agnostic курс проекта
- [x] Зафиксирован memory-first и event-first подход
- [x] Создан `pyproject.toml`
- [x] Создан `src/codecore/` scaffold
- [x] Есть минимальная точка входа `python -m codecore`
- [x] Созданы базовые доменные контракты и модели
- [x] Созданы базовые JSON schemas для `event/provider/skill/mcp`
- [x] Созданы runtime-level manifests: `.codecore/project.yaml`, `providers/registry.yaml`, `mcp/servers.yaml`
- [x] Реализован manifest validation layer на `pydantic` + `PyYAML`
- [x] Есть smoke tests для bootstrap и entrypoint
- [x] Проект собирается как Python package (`sdist` + `wheel`)
- [x] Есть runnable REPL на `prompt_toolkit`
- [x] Есть provider adapters: `LiteLLM` + `mock`
- [x] Есть SQLite / JSONL telemetry layer
- [x] Есть `context manager` и базовый `context composer`
- [x] Есть provider health, broker, fallback и model pinning
- [x] Есть базовые REPL-команды `/help`, `/status`, `/model`, `/ping`, `/add`, `/drop`, `/clear`, `/exit`
- [x] Есть token-budgeted context selection (`token_budget/chunking/selectors`)
- [x] Есть `repo_map` для компактного обзора структуры проекта
- [x] Есть явный file-token accounting и selection reports
- [x] Есть summary-first включение больших файлов
- [x] Есть runtime skill layer: loader, registry, resolver, prompt composer
- [x] Есть built-in skills: `arch`, `backend`, `review`, `telegram`
- [x] Есть `/skill` для pin/unpin skill'ов
- [x] Есть `/pin`, `/unpin`, `/tag`, `/rate`
- [x] Broker учитывает `project-level model preferences` и `allow_vpn_routes`
- [x] Skills реально влияют на system prompt и telemetry events
- [x] Есть SQLite-backed memory store и outcome memories
- [x] Есть recall памяти в prompt composition
- [x] Есть analytics слой и команда `/stats`
- [x] Есть `Phase 5` baseline: `/run`, policy-gated shell execution, summary-first tool outputs
- [x] Есть `git-backed` `/diff` и baseline `/undo`
- [x] Есть approval-backed `/replace` для точечных file edits
- [x] Есть model-driven `/autoedit` для structured edit plans
- [x] Есть snapshot-backed `/rollback`, не зависящий от `git HEAD`
- [x] Есть `/retry` для повторного запуска последней упавшей проверки
- [x] Есть append-only audit trace для CodeCore-managed file changes
- [x] Есть `Phase 6` foundation: agents package, pipeline registry, `/delegate`, isolated worktree baseline
- [x] Есть reviewer-isolated pipeline path и approval-backed apply-back через `change sets`
- [x] Есть `coder -> test -> retry -> review` loop для isolated multi-agent pipelines
- [x] Есть baseline benchmark mode: один task -> несколько model aliases

### Чего пока нет

- [x] Есть базовый execution engine для read-only shell execution
- [x] Есть базовый policy engine для `/run`
- [ ] MCP integration
- [ ] CI pipeline
- [ ] production-grade self-healing verification loop
- [x] Есть базовый security hardening slice: threat model, redaction, untrusted-content guardrails

### Текущая фаза

- `Phase 0` завершена: продукт и архитектура определены
- `Phase 1` завершена: bootstrap репозитория и кодовый каркас готовы
- `Phase 2` завершена: runnable MVP kernel работает
- `Phase 3` завершена: context + skills foundation работает end-to-end
- `Phase 4` завершена: memory + analytics layer работает end-to-end
- `Phase 5` завершена: execution + automation loop работает end-to-end
- `Phase 6` почти завершена: feature set реализован, осталось доказать quality gain
- `Phase 7` начата: security hardening slice реализован

---

## 3. Главные версии и milestones

- [x] `Phase 0` — Product + Architecture Foundation
- [x] `Phase 1` — Repo Bootstrap + Core Contracts
- [x] `Phase 2` — Runnable MVP Kernel (`v0.1`)
- [x] `Phase 3` — Context + Skills (`v0.2`)
- [x] `Phase 4` — Memory + Analytics (`v0.3`)
- [x] `Phase 5` — Execution + Automation (`v0.4`)
- [ ] `Phase 6` — Multi-Agent + Worktrees (`v0.5`)
- [ ] `Phase 7` — Benchmark, Hardening, Release (`v1.0`)

---

## 4. Phase 0 — Product + Architecture Foundation

### Цель

Сформировать канон проекта до начала кодирования.

### Статус

- [x] Сформулирована продуктовая идея CodeCore
- [x] Зафиксированы принципы provider-agnostic архитектуры
- [x] Описана макроархитектура системы
- [x] Описаны memory, skills, MCP, telemetry, governance слои
- [x] Сформирован пакет ADR
- [x] Зафиксирован концентрат best practices именно под CodeCore

### Артефакты

- [x] [start.md](./start.md)
- [x] [architecture.md](./architecture.md)
- [x] [best_practice.md](./best_practice.md)
- [x] [adr/0001-hexagonal-runtime.md](./adr/0001-hexagonal-runtime.md)
- [x] [adr/0002-event-model.md](./adr/0002-event-model.md)
- [x] [adr/0003-memory-taxonomy.md](./adr/0003-memory-taxonomy.md)
- [x] [adr/0004-llm-as-engine.md](./adr/0004-llm-as-engine.md)
- [x] [adr/0005-provider-fabric-and-broker.md](./adr/0005-provider-fabric-and-broker.md)
- [x] [adr/0006-context-and-skill-loading.md](./adr/0006-context-and-skill-loading.md)
- [x] [adr/0007-mcp-federation.md](./adr/0007-mcp-federation.md)
- [x] [adr/0008-verification-and-policy-gates.md](./adr/0008-verification-and-policy-gates.md)
- [x] [adr/0009-parallel-execution.md](./adr/0009-parallel-execution.md)
- [x] [adr/0010-spec-driven-delivery.md](./adr/0010-spec-driven-delivery.md)

### Критерий завершения

- [x] Есть единая архитектурная база, от которой можно начинать код

---

## 5. Phase 1 — Repo Bootstrap + Core Contracts

### Цель

Поднять минимальный кодовый скелет проекта и зафиксировать машинно-исполняемые контракты.

### Задачи

- [x] Создать `pyproject.toml`
- [x] Создать `README.md`
- [x] Создать `src/codecore/__init__.py`
- [x] Создать `src/codecore/__main__.py`
- [x] Создать `src/codecore/bootstrap.py`
- [x] Создать `src/codecore/app.py`
- [x] Создать пакет `src/codecore/domain/`
- [x] Создать пакет `src/codecore/kernel/`
- [x] Создать пакет `src/codecore/infra/`
- [x] Создать пакет `src/codecore/ui/`
- [x] Создать пакет `src/codecore/providers/`
- [x] Создать пакет `src/codecore/context/`
- [x] Создать пакет `src/codecore/skills/`
- [x] Создать пакет `src/codecore/execution/`
- [x] Создать пакет `src/codecore/telemetry/`
- [x] Создать пакет `src/codecore/memory/`
- [x] Создать пакет `src/codecore/governance/`
- [x] Создать пакет `src/codecore/mcp/`
- [x] Создать `tests/` как каркас тестов

### Контракты и модели

- [x] Описать `domain/enums.py`
- [x] Описать `domain/models.py`
- [x] Описать `domain/results.py`
- [x] Описать `domain/events.py`
- [x] Описать `domain/contracts.py`
- [x] Ввести протоколы для `ModelGateway`, `ToolExecutor`, `MemoryStore`, `PolicyEngine`, `TelemetrySink`

### Manifests и schemas

- [x] Создать `docs/schemas/event.schema.json`
- [x] Создать `docs/schemas/provider.schema.json`
- [x] Создать `docs/schemas/skill.schema.json`
- [x] Создать `docs/schemas/mcp-server.schema.json`
- [x] Создать pydantic-модели под manifest'ы
- [x] Создать validation layer для manifest-файлов

### Критерий завершения

- [x] Проект собирается как Python package
- [x] Есть минимальная точка входа `python -m codecore`
- [x] Все несущие интерфейсы уже существуют в коде

---

## 6. Phase 2 — Runnable MVP Kernel (`v0.1`)

### Цель

Сделать минимально работающий терминальный агент.

### Runtime Kernel

- [x] Реализовать `SessionRuntime`
- [x] Реализовать `TurnContext`
- [x] Реализовать `EventBus`
- [x] Реализовать `CommandRouter`
- [x] Реализовать `Orchestrator`
- [x] Реализовать `RuntimeState`

### CLI / REPL

- [x] Подключить `prompt_toolkit`
- [x] Сделать REPL loop
- [x] Подключить history
- [x] Подключить `rich` rendering
- [x] Сделать status bar
- [x] Реализовать `/help`
- [x] Реализовать `/status`
- [x] Реализовать `/exit`
- [x] Реализовать `/clear`

### Provider Layer MVP

- [x] Сделать `providers/registry.py`
- [x] Сделать `providers/health.py`
- [x] Сделать `providers/broker.py`
- [x] Сделать `providers/capabilities.py`
- [x] Сделать `providers/pricing.py`
- [x] Создать `providers/registry.yaml`
- [x] Подключить `litellm` adapter
- [x] Подключить хотя бы один mock adapter для тестов

### Health and routing

- [x] Асинхронный ping провайдеров
- [x] Кэш здоровья провайдеров
- [x] Fallback на следующий провайдер при ошибке
- [x] Переключение модели через alias

### Метрики MVP

- [x] Логировать запросы в SQLite
- [x] Логировать latency
- [x] Логировать token usage
- [x] Логировать cost estimate
- [x] Создать базовую таблицу `sessions`
- [x] Создать базовую таблицу `requests`
- [x] Писать JSONL events

### Команды MVP

- [x] `/model <alias>`
- [x] `/ping`
- [x] `/add <file>`
- [x] `/drop <file>`

### Критерий завершения `v0.1`

- [x] Можно запустить `python -m codecore`
- [x] Можно выбрать провайдера автоматически
- [x] Можно отправить запрос и получить ответ
- [x] Сессия пишет метрики в БД
- [x] Сессия работает как реальный инструмент, а не как демо

---

## 7. Phase 3 — Context + Skills (`v0.2`)

### Цель

Сделать систему управляемого контекста и skill-слой.

### Context System

- [x] Реализовать `context/manager.py`
- [x] Реализовать `context/token_budget.py`
- [x] Реализовать `context/chunking.py`
- [x] Реализовать `context/selectors.py`
- [x] Реализовать `context/composer.py`
- [x] Реализовать `context/repo_map.py`
- [x] Подсчёт токенов по файлам
- [x] Pin/unpin контекста
- [x] Summary-first включение больших файлов

### Skills System

- [x] Реализовать `skills/loader.py`
- [x] Реализовать `skills/registry.py`
- [x] Реализовать `skills/resolver.py`
- [x] Реализовать `skills/composer.py`
- [x] Реализовать `skills/manifests.py`
- [x] Создать директорию `skills/`
- [x] Создать built-in skills: `backend`, `review`, `arch`, `telegram`
- [x] Реализовать progressive disclosure
- [x] Реализовать auto-activation по триггерам

### Project Config

- [x] Создать `.codecore/project.yaml`
- [x] Поддержать project defaults
- [x] Поддержать дефолтные skills на проект
- [x] Поддержать project-level model preferences

### Команды `v0.2`

- [x] `/skill <name>`
- [x] `/tag <type>`
- [x] `/rate <1-5>`

### Критерий завершения `v0.2`

- [x] Агент умеет работать с контекстом как с бюджетом внимания
- [x] Skills реально влияют на system context
- [x] Проект может задавать собственные дефолты без правки ядра
- [x] Большие файлы не ломают prompt budget и попадают в контекст через summary-first

---

## 8. Phase 4 — Memory + Analytics (`v0.3`)

### Цель

Дать системе память и измеримую самоадаптацию.

### Memory Layer

- [x] Реализовать `memory/store.py`
- [x] Реализовать `memory/taxonomy.py`
- [x] Реализовать `memory/recall.py`
- [x] Реализовать `memory/summarizer.py`
- [x] Реализовать `memory/patterns.py`
- [x] Реализовать `memory/rankings.py`
- [x] Ввести `session/project/global/outcome/governance` уровни памяти
- [x] Сделать selective write policy
- [x] Сделать selective recall policy

### Analytics

- [x] Реализовать `telemetry/analytics.py`
- [x] Реализовать `/stats`
- [x] Реализовать aggregation по моделям
- [x] Реализовать aggregation по task tags
- [x] Реализовать skill effectiveness scoring
- [x] Реализовать provider reliability scoring
- [x] Реализовать cost per successful task

### Learning Loops

- [x] Model ranking by task type
- [x] Skill ranking by outcome quality
- [x] Route ranking by quality/cost
- [x] Recommendation engine для модели на старте задачи

### Критерий завершения `v0.3`

- [x] CodeCore умеет рекомендовать модель на основе собственной истории
- [x] `/stats` помогает принимать решения, а не просто показывает цифры
- [x] Память усиливает следующие задачи, а не просто хранит архив

---

## 9. Phase 5 — Execution + Automation (`v0.4`)

### Цель

Сделать из CodeCore не только ответчик, но и полноценный агент исполнения.

### Execution Engine

- [x] Реализовать `execution/shell.py`
- [x] Реализовать `execution/files.py`
- [x] Реализовать `execution/patches.py`
- [x] Реализовать `execution/git.py`
- [x] Реализовать `execution/tests.py`
- [x] Реализовать `execution/sandbox.py`
- [x] Реализовать `execution/approvals.py`
- [x] Добавить append-only audit log для file changes

### Commands and workflows

- [x] `/run <cmd>`
- [x] `/autoedit <instruction>`
- [x] `/replace <path> <old> <new>`
- [x] `/rollback`
- [x] `/retry`
- [x] `/undo`
- [x] `/diff`
- [x] Автоподмешивание результатов проверок в контекст
- [x] Error loop: failed run -> retry with context
- [x] Summary-first логика для tool outputs

### Safe automation

- [x] Approval gates по классам риска
- [x] Policy checks перед destructive actions
- [x] Запрет на опасные действия без подтверждения
- [x] Audit trace по всем CodeCore-managed file changes

### Критерий завершения `v0.4`

- [x] CodeCore может выполнить задачу от промпта до патча и проверки
- [x] Есть безопасный цикл исправления ошибок
- [x] Инструмент не теряет управляемость при реальном file editing

---

## 10. Phase 6 — Multi-Agent + Worktrees (`v0.5`)

### Цель

Поддержать сложные задачи через несколько ролей и изолированные execution contexts.

### Multi-Agent Layer

- [x] Реализовать `agents/classifier.py`
- [x] Реализовать `agents/planner.py`
- [x] Реализовать `agents/coder.py`
- [x] Реализовать `agents/reviewer.py`
- [x] Реализовать `agents/evaluator.py`
- [x] Реализовать `agents/synthesizer.py`
- [x] Реализовать pipeline definitions
- [x] Реализовать role-based routing

### Parallel Execution

- [x] Поддержка isolated execution contexts
- [x] Поддержка git worktrees
- [x] Отдельный context snapshot на агента
- [x] Merge discipline по change sets
- [x] Reviewer как отдельный execution role

### Pipelines

- [x] `planner -> coder`
- [x] `planner -> coder -> reviewer`
- [x] `coder -> test -> retry -> review`
- [x] Benchmark mode: один запрос -> N моделей

### Критерий завершения `v0.5`

- [ ] CodeCore умеет решать сложные задачи цепочкой ролей
- [ ] Параллельная работа не ломает репозиторий
- [ ] Агентные pipeline реально дают выигрыш в качестве

---

## 11. Phase 7 — Benchmark, Hardening, Release (`v1.0`)

### Цель

Довести CodeCore до зрелого, устойчивого инструмента.

### Hardening

- [ ] Покрыть ядро тестами
- [ ] Покрыть manifest validation тестами
- [ ] Покрыть provider broker тестами
- [ ] Покрыть policy engine тестами
- [ ] Покрыть execution engine интеграционными тестами
- [ ] Покрыть memory/analytics regression tests

### Security and governance

- [x] Threat model document
- [x] Secret hygiene checks
- [x] Input sanitization for untrusted content
- [x] Prompt injection protections
- [ ] MCP trust scoring
- [ ] Cost guardrails
- [ ] Rate limiting / budget limiting

### DevOps and release

- [ ] CI workflow
- [ ] Lint + typecheck + tests in CI
- [ ] Versioning policy
- [ ] Packaging / install story
- [ ] Example config templates
- [ ] Bootstrap command for new users

### Product validation

- [ ] Сравнить CodeCore vs Aider/Claude Code/Codex на реальных задачах
- [ ] Собрать benchmark dataset своих задач
- [ ] Сравнить quality/cost/latency
- [ ] Зафиксировать сильные и слабые маршруты
- [ ] Подготовить релизный README и docs

### Критерий завершения `v1.0`

- [ ] CodeCore стабильно используется в реальных задачах
- [ ] Имеет измеримые преимущества на собственных сценариях
- [ ] Достаточно документирован, чтобы другой инженер смог развернуть и использовать

---

## 12. Сквозные треки, которые идут через все фазы

### A. Documentation Track

- [ ] Поддерживать актуальность `start.md`
- [ ] Поддерживать актуальность `architecture.md`
- [ ] Поддерживать актуальность `best_practice.md`
- [ ] Добавлять новые ADR при смене несущих решений
- [ ] Вести changelog архитектурных сдвигов

### B. Quality Track

- [ ] Unit tests
- [ ] Integration tests
- [ ] Smoke tests
- [ ] Manual acceptance scenarios
- [ ] Benchmark tasks

### C. Telemetry Track

- [ ] Полнота event logging
- [x] Projection tables в SQLite
- [ ] Cost accounting
- [ ] Latency tracking
- [ ] Reliability tracking

### D. Security Track

- [ ] Approval classes
- [ ] Policy engine maturity
- [ ] Tool allowlists
- [ ] Secret redaction
- [ ] Auditability

### E. Product Fit Track

- [ ] Реальные задачи внутри репозитория вести через CodeCore
- [ ] Отмечать, где агент помогает, а где мешает
- [ ] Пополнять skills на основе реальных повторяющихся работ
- [ ] Пополнять memory rules на основе неудач и улучшений

---

## 13. Что не делать раньше времени

- [ ] Не строить vector DB-first память до необходимости
- [ ] Не строить plugin marketplace до рабочего ядра
- [ ] Не строить GUI раньше стабильного CLI
- [ ] Не строить сложные multi-agent graphs раньше single-agent reliability
- [ ] Не подключать десятки MCP серверов до trust and ranking layer
- [ ] Не раздувать `CLAUDE.md`-подобный монолит вместо skill/policy architecture

---

## 14. Ближайшие следующие действия

### Следующий обязательный этап

- [ ] Закрыть `Phase 6` через benchmark evidence и quality proof loops

### Конкретный ближайший срез

- [x] `agents/classifier.py`
- [x] `agents/planner.py`
- [x] `agents/coder.py`
- [x] pipeline definitions
- [x] isolated execution contexts
- [x] git worktrees baseline

### После этого

- [ ] зафиксировать benchmark evidence и quality deltas
- [ ] начать CI + release hardening slice

---

## 15. Definition of Done

### Для документальной задачи

- [ ] Решение зафиксировано в `.md`
- [ ] Формулировки не противоречат `architecture.md` и ADR

### Для кодовой задачи

- [ ] Код существует в репозитории
- [ ] Код подключён в runtime или validation flow
- [ ] Есть тест или проверяемый сценарий
- [ ] Обновлена документация при необходимости

### Для milestone

- [ ] Все обязательные задачи этапа выполнены
- [ ] Выполнен критерий завершения этапа
- [ ] Следующая фаза может начаться без архитектурной неопределенности
