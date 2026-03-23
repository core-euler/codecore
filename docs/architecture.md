# CodeCore Architecture
## Архитектурный blueprint развивающейся оболочки для AI-агентов
`v1 · 2026-03-22`

---

## 1. Миссия

CodeCore строится не как CLI-обертка над одной LLM, а как **операционная среда для разработки**, в которой модели, инструменты, знания, навыки и результаты работы собираются в единую саморегулирующуюся систему.

Это не просто агент. Это:

- дом для множества моделей;
- единая точка входа для Skills, MCP и tool execution;
- среда накопления инженерного опыта;
- система, которая **измеряет**, **сравнивает**, **адаптирует** и **эволюционирует** собственные пайплайны.

Важный архитектурный тезис: **LLM здесь не инженерная система, а исполняющий двигатель внутри инженерной системы**. Качество должно определяться не “магией конкретной модели”, а тем, насколько хорошо CodeCore управляет правилами, контекстом, skill-слоем, верификацией, памятью и маршрутизацией.

Ключевой принцип: **любая модель, любой backend, любой transport, любой tool server должен подключаться через единый контракт**.

---

## 2. Непереговорные архитектурные принципы

### 2.1 Provider Fabric, а не provider binding

Провайдеры не вшиваются в core-логику. Все внешние LLM, локальные движки и OpenAI-compatible API подключаются через слой адаптеров и capability profile.

### 2.1.1 Model invariance as design target

CodeCore должен проектироваться так, чтобы **разные модели давали сопоставимо успешный результат в одной и той же среде**, если им даны одинаковые:

- ограничения;
- skills;
- контекст;
- pipeline;
- verification loop;
- policies.

Это не означает, что все модели станут идентичны по качеству. Это означает, что основная инженерная устойчивость переносится из модели в систему.

Иными словами:

- модель отвечает за генерацию и рассуждение;
- среда отвечает за дисциплину, воспроизводимость и контроль качества;
- оператор усиливает результат, но не должен быть единственным носителем процесса.

### 2.2 Event-sourced runtime

Каждое значимое действие системы оформляется как событие:

- старт сессии;
- выбор модели;
- подключение skill;
- загрузка контекста;
- tool call;
- patch application;
- user feedback;
- тестовый результат;
- fallback;
- ошибка;
- итоговая оценка результата.

Система должна помнить **не только что ответила модель**, но и **как она пришла к результату**, в каком окружении, с какими файлами, инструментами и исходом.

### 2.3 Memory is metadata first

Память строится не как свалка логов, а как структурированная база:

- какие модели лучше решают какие классы задач;
- какие skills усиливают результат;
- какие MCP-серверы полезны в каких проектах;
- какие паттерны исправлений чаще всего работают;
- какие ошибки повторяются.

### 2.4 Separation of concerns

Нужно жестко разделить:

- orchestration;
- provider access;
- execution;
- memory;
- telemetry;
- UX;
- policies/governance.

### 2.5 Human-guided autonomy

Агент может действовать самостоятельно, но архитектура всегда позволяет:

- ограничить доступ;
- включить approval gates;
- откатить изменения;
- проследить причинно-следственную цепочку.

### 2.6 Extensibility by manifest

Skills, MCP servers, providers, pipelines, policies и knowledge packs должны подключаться через manifest-driven механику, а не через ручную правку ядра.

---

## 3. Макроархитектура

Система делится на 7 уровней.

### 3.1 Experience Layer

Пользовательские интерфейсы:

- terminal REPL;
- non-interactive batch mode;
- TUI dashboards;
- headless agent mode;
- API/server mode в будущем.

Задача слоя: принимать intent, показывать state, подтверждения, diff, метрики и историю.

### 3.2 Runtime Kernel

Центральное ядро исполнения сессии.

Отвечает за:

- lifecycle сессии;
- command routing;
- orchestration turn-by-turn;
- event bus;
- state snapshot;
- policy checks;
- coordination между агентами и subsystem-ами.

Kernel ничего не знает о конкретном провайдере, конкретной базе памяти или конкретном MCP-сервере. Он работает через контракты.

### 3.3 Intelligence Plane

Слой агентного мышления.

Включает:

- planner;
- coder;
- reviewer;
- synthesizer;
- evaluator;
- task classifier;
- pipeline selector.

Это не одна модель, а orchestration из ролей. Для простой задачи может работать только `coder`. Для сложной - цепочка `classifier -> planner -> coder -> reviewer -> evaluator`.

### 3.4 Execution Plane

Слой реальных действий над окружением:

- shell execution;
- file read/write;
- patch generation/apply;
- git integration;
- test/lint runners;
- sandboxing;
- retry/error loop.

Этот слой должен быть полностью трассируемым и безопасным.

### 3.5 Knowledge Plane

Слой памяти и накопления инженерной мудрости.

Компоненты:

- session memory;
- project memory;
- global memory;
- skill registry;
- MCP registry;
- pattern library;
- model performance memory;
- artifact index.

### 3.6 Integration Plane

Слой внешних подключений:

- LLM providers;
- local models (`ollama`, `llama.cpp`, `vllm`, `openai-compatible`);
- MCP servers;
- embeddings backends;
- vector stores в будущем;
- issue trackers / git hosting / CI integrations в будущем.

### 3.7 Telemetry and Governance Plane

Слой саморегуляции.

Компоненты:

- structured logs;
- request metrics;
- quality scoring;
- route ranking;
- policy engine;
- anomaly detection;
- cost governance;
- reliability scoring;
- adaptive recommendations.

Именно этот слой превращает оболочку в развивающуюся систему.

---

## 4. Целевой runtime-поток

### 4.1 Startup

1. Загружается конфиг пользователя и проекта.
2. Инициализируются registries: providers, skills, MCP, policies, pipelines.
3. Выполняется health scan доступных провайдеров и tool servers.
4. Подгружается глобальная и проектная память.
5. Строится стартовый runtime snapshot.

### 4.2 На каждый пользовательский запрос

1. `Intent Classifier` определяет тип задачи: `ask`, `edit`, `review`, `debug`, `arch`, `run`, `multi-step`.
2. `Pipeline Selector` выбирает pipeline.
3. `Provider Broker` подбирает оптимальную модель или группу моделей.
4. `Context Composer` собирает контекст:
   - системный базовый prompt;
   - активные skills;
   - project memory;
   - релевантные file chunks;
   - repo map summary;
   - результаты прошлых похожих задач;
   - MCP resources/tool hints.
5. Агент выполняет reasoning/response/tool planning.
6. `Execution Plane` исполняет действия.
7. `Evaluator` анализирует outcome:
   - завершилась ли задача;
   - были ли ошибки;
   - прошли ли тесты;
   - нужен ли retry/fallback.
8. `Telemetry Plane` пишет события, метрики и outcome score.
9. `Knowledge Plane` обновляет память и рейтинги.
10. Пользователь получает ответ, diff, next action или status.

### 4.3 На завершение сессии

1. Строится summary сессии.
2. В память сохраняются полезные artifacts.
3. Обновляются quality profiles моделей, skills и pipelines.
4. Формируется session report.

---

## 5. Физическая структура проекта

Ниже целевая структура, от которой можно сразу стартовать реализацию.

```text
codecore/
├── pyproject.toml
├── README.md
├── docs/
│   ├── start.md
│   ├── architecture.md
│   ├── adr/
│   │   ├── 0001-hexagonal-runtime.md
│   │   ├── 0002-event-model.md
│   │   └── 0003-memory-taxonomy.md
│   └── schemas/
│       ├── event.schema.json
│       ├── skill.schema.json
│       ├── provider.schema.json
│       └── mcp-server.schema.json
├── src/
│   └── codecore/
│       ├── __init__.py
│       ├── __main__.py
│       ├── bootstrap.py
│       ├── app.py
│       ├── domain/
│       │   ├── enums.py
│       │   ├── events.py
│       │   ├── models.py
│       │   ├── results.py
│       │   └── contracts.py
│       ├── kernel/
│       │   ├── session.py
│       │   ├── runtime_state.py
│       │   ├── command_router.py
│       │   ├── event_bus.py
│       │   ├── pipeline.py
│       │   └── orchestrator.py
│       ├── ui/
│       │   ├── repl.py
│       │   ├── commands.py
│       │   ├── statusbar.py
│       │   ├── tables.py
│       │   └── renderers.py
│       ├── providers/
│       │   ├── registry.py
│       │   ├── broker.py
│       │   ├── health.py
│       │   ├── pricing.py
│       │   ├── capabilities.py
│       │   └── adapters/
│       │       ├── base.py
│       │       ├── litellm_adapter.py
│       │       ├── openai_compat.py
│       │       ├── ollama_adapter.py
│       │       └── mock_adapter.py
│       ├── agents/
│       │   ├── classifier.py
│       │   ├── planner.py
│       │   ├── coder.py
│       │   ├── reviewer.py
│       │   ├── evaluator.py
│       │   └── synthesizer.py
│       ├── context/
│       │   ├── manager.py
│       │   ├── repo_map.py
│       │   ├── token_budget.py
│       │   ├── selectors.py
│       │   ├── chunking.py
│       │   └── composer.py
│       ├── skills/
│       │   ├── loader.py
│       │   ├── registry.py
│       │   ├── resolver.py
│       │   ├── composer.py
│       │   └── manifests.py
│       ├── mcp/
│       │   ├── registry.py
│       │   ├── client.py
│       │   ├── bridge.py
│       │   ├── discovery.py
│       │   └── manifests.py
│       ├── execution/
│       │   ├── shell.py
│       │   ├── sandbox.py
│       │   ├── patches.py
│       │   ├── files.py
│       │   ├── git.py
│       │   ├── tests.py
│       │   └── approvals.py
│       ├── memory/
│       │   ├── store.py
│       │   ├── taxonomy.py
│       │   ├── recall.py
│       │   ├── summarizer.py
│       │   ├── patterns.py
│       │   └── rankings.py
│       ├── telemetry/
│       │   ├── tracker.py
│       │   ├── events.py
│       │   ├── analytics.py
│       │   ├── exporters.py
│       │   └── dashboards.py
│       ├── governance/
│       │   ├── policy_engine.py
│       │   ├── route_ranker.py
│       │   ├── quality_engine.py
│       │   ├── cost_guard.py
│       │   └── safety.py
│       ├── infra/
│       │   ├── settings.py
│       │   ├── paths.py
│       │   ├── logging.py
│       │   ├── sqlite.py
│       │   └── clock.py
│       └── assets/
│           ├── base_system_prompt.md
│           ├── builtin_skills/
│           └── policies/
├── skills/
│   ├── backend.md
│   ├── review.md
│   ├── arch.md
│   └── telegram.md
├── providers/
│   ├── registry.yaml
│   └── routes.yaml
├── mcp/
│   ├── servers.yaml
│   └── profiles/
├── .codecore/
│   ├── project.yaml
│   ├── memory/
│   ├── snapshots/
│   └── cache/
└── .codecore-home/
    ├── global.yaml
    ├── registry.db
    ├── events/
    ├── memory/
    ├── sessions/
    ├── artifacts/
    └── exports/
```

---

## 6. Главные подсистемы и контракты

## 6.1 Kernel

`kernel` - единственная точка координации runtime.

Ключевые сущности:

- `SessionRuntime` - живое состояние сессии;
- `TurnContext` - состояние одного пользовательского хода;
- `CommandRouter` - маршрутизация `/commands`;
- `Orchestrator` - выполнение пайплайна;
- `EventBus` - публикация доменных событий;
- `PipelineDefinition` - декларативный сценарий работы агентов.

Контракт ядра:

- принимать intent;
- выбирать pipeline;
- запрашивать зависимости через интерфейсы;
- не зависеть от деталей infra.

## 6.2 Provider Fabric

Центральный интерфейс:

```python
class ModelGateway(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResult: ...
    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]: ...
    async def health(self) -> HealthStatus: ...
    def capabilities(self) -> ModelCapabilities: ...
```

Провайдер описывается как manifest + adapter.

Manifest хранит:

- `provider_id`;
- `transport`;
- `base_url`;
- `auth_strategy`;
- `models`;
- `geo_constraints`;
- `costs`;
- `rate_limits`;
- `supports_tools`;
- `supports_json`;
- `supports_vision`;
- `max_context`;
- `priority`.

`ProviderBroker` выбирает не “любимую модель”, а лучшую комбинацию по профилю задачи:

- capability fit;
- success history;
- latency;
- доступность;
- стоимость;
- локальность;
- наличие VPN;
- user policy.

При этом broker и runtime должны стремиться к **quality normalization**:

- сильные модели ускоряют и удешевляют путь до результата;
- слабые или дешёвые модели не должны выпадать из системы полностью, если их можно усилить правилами, skill stack, better context composition и verification loops;
- смена модели не должна ломать сам рабочий процесс.

## 6.3 Agent Pipeline Layer

Agent layer должен быть role-based.

Базовые роли:

- `ClassifierAgent` - определяет тип работы;
- `PlannerAgent` - строит план;
- `CoderAgent` - пишет решение;
- `ReviewerAgent` - ищет риски и регрессии;
- `EvaluatorAgent` - оценивает качество исхода;
- `SynthesizerAgent` - собирает ответ пользователю.

Пайплайн описывается декларативно, например:

```yaml
id: edit_safe
steps:
  - agent: classifier
  - agent: planner
  - agent: coder
  - tool: patch_apply
  - tool: test_runner
  - agent: reviewer
  - agent: synthesizer
policy:
  approvals: on-write
  fallback_on_error: true
```

Это позволяет эволюционировать без переписывания ядра.

## 6.4 Context System

Контекст - не список файлов, а управляемый бюджет внимания.

Подсистема должна уметь:

- строить `repo map`;
- разрезать файлы на chunks;
- считать token cost;
- выделять hot files;
- подтягивать соседние зависимости;
- исключать шум;
- сохранять pinned context;
- строить prompt context по budget policy.

Основной принцип: в prompt попадает не всё, а **минимально достаточный контекст**.

## 6.5 Skill System

Skill - это версионированный knowledge pack.

Skill должен включать:

- manifest;
- system prompt fragment;
- tags;
- scope;
- optional heuristics;
- optional tool preferences;
- optional quality rules.

Пример manifest:

```yaml
name: backend
version: 1
summary: FastAPI backend development
triggers: [python, fastapi, api, async]
inject:
  system_prompt: true
  quality_rules: true
weights:
  planner: 0.3
  coder: 0.8
  reviewer: 0.9
```

`SkillResolver` должен поддерживать:

- ручную активацию;
- авто-подбор по задаче;
- project defaults;
- ranking по эффективности.

## 6.6 MCP Federation Layer

MCP не должен быть внешним “дополнением”. Он должен стать нативным слоем возможностей.

`MCPRegistry` хранит:

- доступные servers;
- их tools/resources/prompts;
- auth requirements;
- performance profile;
- trust level;
- project relevance.

`MCPBridge` предоставляет unified API для агента:

- discover tools;
- call tool;
- read resource;
- cache result;
- log usage;
- rate usefulness.

В памяти нужно сохранять, какие MCP-серверы реально полезны для каких типов задач.

## 6.7 Execution Engine

Execution Engine обязан быть детерминированным и наблюдаемым.

Подкомпоненты:

- `ShellExecutor`;
- `PatchEngine`;
- `FileSystemOps`;
- `GitOps`;
- `ApprovalGate`;
- `RetryLoop`.

Execution record хранит:

- команду;
- cwd;
- env scope;
- stdout/stderr summary;
- exit code;
- duration;
- sandbox mode;
- affected files.

## 6.8 Memory System

Память делится на 5 слоев.

### A. Ephemeral Session Memory

Краткоживущая память текущей сессии:

- последние сообщения;
- активные файлы;
- текущий task tag;
- временные решения;
- локальные ошибки.

### B. Project Memory

Память внутри конкретного репозитория:

- соглашения проекта;
- архитектурные решения;
- важные файлы;
- повторяющиеся команды;
- частые ошибки;
- полезные skills и MCP servers.

### C. Global Memory

Кросс-проектная память:

- общие инженерные паттерны;
- рейтинги моделей;
- эффективность pipelines;
- библиотека типовых исправлений.

### D. Outcome Memory

Хранилище исходов:

- что сработало;
- что не сработало;
- при каких условиях;
- с каким quality score;
- какова была цена результата.

### E. Governance Memory

Память ограничений и рисков:

- запрещенные действия;
- дорогие маршруты;
- небезопасные паттерны;
- нестабильные провайдеры.

## 6.9 Telemetry and Governance

Это слой, который превращает CodeCore в самонастраивающуюся систему.

Он должен считать не только технические метрики, но и инженерную эффективность.

Основные scoring dimensions:

- `success_score`;
- `user_rating`;
- `tool_efficiency`;
- `patch_acceptance_rate`;
- `test_pass_rate`;
- `retry_count`;
- `cost_efficiency`;
- `latency_profile`;
- `provider_reliability`;
- `skill_effectiveness`;
- `mcp_usefulness`.

На основании этого `RouteRanker` и `QualityEngine` должны адаптировать:

- выбор модели;
- выбор pipeline;
- выбор skills;
- необходимость reviewer step;
- необходимость fallback;
- предупреждения о рисках.

---

## 7. Данные и хранилища

Архитектурно лучше использовать гибридный storage, а не пытаться хранить всё в одном месте.

### 7.1 SQLite как control plane database

SQLite хранит структурированные сущности и быстрые выборки.

Основные таблицы:

- `sessions`
- `turns`
- `events`
- `providers`
- `models`
- `model_stats`
- `skills`
- `skill_usage`
- `mcp_servers`
- `mcp_usage`
- `tool_calls`
- `file_changes`
- `evaluations`
- `artifacts`
- `memories`
- `pipelines`
- `pipeline_stats`

### 7.2 JSONL/Event Log как source of truth for replay

Каждое событие дополнительно сохраняется append-only в JSONL:

- удобно для replay;
- удобно для оффлайн-анализа;
- не ломает историчность;
- можно строить будущий DSL dataset.

### 7.3 Filesystem object store

Файловое хранилище для:

- summaries;
- repo maps;
- prompt snapshots;
- tool outputs;
- generated patches;
- exported reports.

### 7.4 Optional vector memory later

На старте векторное хранилище не обязательно. Достаточно:

- metadata index;
- keyword recall;
- summaries;
- heuristics.

Vector search добавляется только когда реально появится боль по recall quality.

---

## 8. Единая таксономия метаданных

Чтобы система действительно эволюционировала, у каждого события и артефакта должен быть нормализованный набор полей.

Минимальная metadata envelope:

```json
{
  "id": "uuid",
  "kind": "tool_call",
  "session_id": "uuid",
  "turn_id": "uuid",
  "project_id": "repo-hash",
  "timestamp": "2026-03-22T12:00:00Z",
  "task_tag": "debug",
  "provider_id": "deepseek",
  "model_id": "deepseek-chat",
  "pipeline_id": "edit_safe",
  "skill_ids": ["backend", "review"],
  "mcp_server_ids": ["figma", "filesystem"],
  "input_hash": "...",
  "outcome": "success",
  "cost_usd": 0.0021,
  "latency_ms": 1840,
  "quality_score": 0.84
}
```

Без этой нормализации нельзя построить качественную адаптацию.

---

## 9. Саморегуляция и эволюция

CodeCore должен развиваться не через магию, а через четкие feedback loops.

### 9.1 Model Learning Loop

После каждого outcome обновляется профиль модели:

- для каких задач работает лучше;
- где дорогая и неоправданная;
- где нестабильна;
- где хороша как planner, но плоха как coder.

### 9.2 Skill Learning Loop

Оценивается не просто “skill использовался”, а:

- повысил ли он качество;
- снизил ли число retries;
- улучшил ли review findings;
- не перегрузил ли context.

### 9.3 MCP Learning Loop

Система должна понимать:

- какие MCP tools реально полезны;
- какие только замедляют pipeline;
- какие сервера надежны;
- каким серверам нужен trust downgrade.

### 9.4 Pipeline Learning Loop

Сравниваются пайплайны:

- `coder only`
- `planner -> coder`
- `planner -> coder -> reviewer`
- `edit -> test -> retry -> review`

Выигрывает не самый умный, а самый эффективный по качеству/стоимости/времени.

### 9.5 Human Feedback Loop

Оценка пользователя не должна быть декоративной. Она влияет на:

- route ranking;
- preferred model by task;
- preferred skill stack;
- reviewer strictness;
- proposal style.

---

## 10. Конфигурационная модель

Конфиг должен быть многоуровневым.

### 10.1 Уровни конфигурации

1. `global` - пользовательские дефолты.
2. `project` - правила и предпочтения репозитория.
3. `session` - временные overrides.
4. `pipeline` - настройки конкретного сценария.
5. `runtime` - вычисленные значения на основе health, memory и policy.

### 10.2 Приоритеты

`runtime > session > project > global > builtin defaults`

### 10.3 Ключевые конфиги

- default provider strategy;
- fallback policy;
- approval policy;
- memory retention;
- skill auto-activation;
- MCP allowlist/denylist;
- tool budgets;
- cost limits;
- retry limits;
- reviewer strictness.

---

## 11. Безопасность и контроль

Чтобы оболочка могла стать домом для автономных агентов, контроль должен быть встроен в архитектуру.

### 11.1 Approval Gates

Действия делятся по классам риска:

- read-only;
- workspace write;
- destructive;
- networked;
- secret-touching;
- external side effects.

### 11.2 Policy Engine

Policy engine оценивает:

- можно ли выполнить действие;
- нужен ли user approval;
- нужен ли safer alternative;
- нужно ли скрыть часть вывода;
- нужно ли понизить маршрут до более безопасного.

### 11.3 Auditability

Для любого изменения должно быть можно ответить:

- кто инициировал;
- какая модель предложила;
- какой tool применил;
- какой diff был внесен;
- какая проверка прошла или не прошла.

---

## 12. Почему эта архитектура сильнее обычного AI CLI

Обычный AI CLI:

- одна модель;
- короткая память;
- минимум метрик;
- слабая объяснимость;
- нет общего knowledge plane;
- skills и tools живут отдельно;
- история почти не используется для улучшения маршрутов.

CodeCore по этой архитектуре:

- provider-agnostic;
- pipeline-native;
- skill-native;
- MCP-native;
- event-driven;
- memory-centric;
- quality-aware;
- self-regulating;
- пригоден как для одного агента, так и для целой экосистемы агентов.

---

## 13. Что делать первым: реализационный срез v0.1

Чтобы не утонуть в масштабе, первый production slice должен включать только несущий каркас.

### v0.1 Core Slice

Реализовать сразу:

- `ui/repl.py`
- `kernel/session.py`
- `kernel/orchestrator.py`
- `providers/registry.py`
- `providers/broker.py`
- `providers/adapters/litellm_adapter.py`
- `context/manager.py`
- `telemetry/tracker.py`
- `infra/sqlite.py`
- `execution/shell.py`
- `skills/loader.py`
- `providers/registry.yaml`
- `.codecore/project.yaml`

Не реализовывать в v0.1 полностью:

- multi-agent graphs;
- vector memory;
- сложный governance scoring;
- полноценный MCP federation layer;
- auto-learning heuristics beyond simple rankings.

Но архитектурные интерфейсы под них должны существовать сразу.

---

## 14. Архитектурный тезис

CodeCore должен быть построен как **agent operating system for software development**.

Не клиент к модели.
Не чат-оболочка.
Не набор команд.

А среда, в которой:

- модели взаимозаменяемы;
- качество как можно меньше зависит от “любимой модели” и как можно больше зависит от устройства среды;
- инструменты унифицированы;
- знания индексируются;
- навыки подключаются модульно;
- опыт превращается в метаданные;
- метаданные превращаются в лучшие маршруты;
- лучшие маршруты превращаются в устойчивую инженерную эволюцию.

Если `start.md` - это идея продукта, то эта архитектура задает его несущий скелет.
