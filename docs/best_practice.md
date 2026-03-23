# CodeCore Best Practice
## Концентрат лучших практик LLM-driven разработки для архитектуры CodeCore
`v1 · 2026-03-22`

---

## 1. Назначение документа

Этот документ не пересказывает весь массив `docs/best_practice/`. Он фиксирует только те практики, которые должны стать **архитектурными правилами CodeCore**.

Цель:

- встроить в CodeCore сильные паттерны агентной разработки;
- обеспечить совместимость с лучшими workflow работы через LLM;
- убрать шум, опасные упрощения и модные, но вредные антипаттерны;
- превратить CodeCore в систему, которая не просто вызывает модели, а **повышает качество разработки через дисциплину, верификацию, память и управление контекстом**.

Главный тезис:

> CodeCore должен быть не “ещё одним AI CLI”, а инженерной средой, в которой лучшие практики LLM-разработки встроены в сам runtime.

Отдельный целевой принцип:

> LLM в CodeCore - это двигатель, а не вся машина. Мы строим такую среду, в которой разные модели при прочих равных должны приходить к сопоставимо успешному результату за счет правил, skills, context engineering, verification и memory.

---

## 2. Что CodeCore принимает как основу

Из изученного массива для CodeCore обязательны следующие базовые принципы.

### 2.1 Agent loop обязателен

CodeCore не должен останавливаться на паттерне `prompt -> answer`.
Любой серьёзный сценарий строится как:

`Plan -> Execute -> Verify -> Adapt`

Следствия для архитектуры:

- у каждой задачи должны быть `goal`, `constraints`, `done criteria`;
- выполнение должно быть итеративным, а не одноразовым;
- проверка результата обязательна до финального ответа;
- повтор цикла допустим только при наличии причины: failed test, violated policy, missing artifact.

### 2.2 Spec-driven важнее vibe-driven

CodeCore должен усиливать режим `spec -> plan -> tasks -> implementation -> verification`, а не хаотичный “сгенерируй что-нибудь”.

Следствия:

- система должна уметь работать со спецификациями как first-class artifacts;
- крупные задачи должны раскладываться на дискретные шаги;
- негативный prompt обязателен: что не входит в scope, должно быть сформулировано явно;
- архитектурные решения должны фиксироваться раньше массовой генерации кода.

### 2.3 Context engineering важнее prompt engineering

Качество ответа сильнее зависит от качества контекста, чем от красоты формулировки запроса.

Следствия:

- контекстный бюджет должен управляться явно;
- вся нерелевантная история, шумные tool outputs и устаревшие факты должны удаляться или сжиматься;
- система обязана хранить важные решения, ограничения и статус в устойчивой форме;
- compact не должен уничтожать причинно-следственную цепочку.

### 2.4 Verification beats confidence

Фразы вида “должно работать” считаются дефектом процесса.

Следствия:

- CodeCore должен завершать цикл только после evidence;
- evidence может быть: тесты, lint, typecheck, runtime output, review findings, human approval;
- каждое изменение должно быть связано с проверкой или объяснением, почему она невозможна.

### 2.5 Wrong information is worse than missing information

Основной источник деградации агентных систем - не нехватка контекста, а загрязнённый контекст.

Следствия:

- лучше дать меньше, но точнее;
- инструменты должны отдавать summary-first output;
- модель не должна видеть гигантские неотфильтрованные логи без необходимости;
- noisy MCP/tool definitions нужно строго контролировать.

### 2.6 Среда важнее конкретной модели

CodeCore должен исходить из жёсткой инженерной позиции:

- оператор влияет на результат;
- модели различаются по силе;
- но основной носитель качества должен находиться в системе, а не в конкретной LLM.

Следствия:

- правила должны быть явными и переносимыми между моделями;
- skills не должны зависеть от особенностей одной платформы;
- verification должен быть внешним по отношению к модели;
- успех должен определяться pipeline и evidence, а не харизмой ответа;
- при замене модели рабочий процесс должен деградировать мягко, а не разваливаться.

---

## 3. Архитектурные требования к CodeCore

## 3.1 Orchestrator должен быть policy-aware

Оркестратор обязан принимать решения не только по intent пользователя, но и с учетом:

- стоимости;
- качества исторических маршрутов;
- риска действия;
- необходимости верификации;
- текущего состояния контекста.

Иными словами: orchestration не может быть “тонкой прокладкой” над chat completion.

## 3.2 Skills должны быть native, modular, on-demand

Skills в CodeCore должны восприниматься не как markdown-заметки, а как **workflow packages**.

Требования:

- skill имеет manifest и измеряемые метаданные;
- metadata загружается всегда, полное тело - только по триггеру;
- большие reference-материалы выносятся в supporting files;
- skill может содержать scripts, templates, examples, policies;
- система должна уметь оценивать эффективность skill по outcomes.

## 3.3 MCP должен быть встроенным, но не фетишизированным

MCP - важный стандарт, но не всё должно идти через MCP.

Требования:

- MCP используется там, где он даёт унификацию, discoverability и reusable integration;
- простые операции предпочтительно выполнять через проверяемые CLI / локальные tools, если это дешевле и чище по контексту;
- capabilities MCP должны индексироваться и ранжироваться по полезности;
- trust model для MCP servers обязателен.

## 3.4 Memory должна быть структурированной, а не “chat history forever”

CodeCore не должен хранить память как бесконечный transcript.

Требования:

- память делится минимум на session, project, global, outcome и governance;
- сохраняются не все сообщения подряд, а решения, ограничения, ошибки, результаты, рейтинги и повторяющиеся паттерны;
- recall должен быть selective;
- память обязана быть привязана к метаданным: task type, model, skill, tool, cost, success.

## 3.5 Hooks/policies должны быть детерминированными

Если действие должно выполняться всегда, это не prompt, а policy/hook.

Требования:

- обязательные проверки не живут в “советах модели”;
- lint/test/secret checks/approval gates должны быть реализованы детерминированно;
- поведение на high-risk actions должно задаваться policy engine, а не доброй волей модели.

---

## 4. Операционная модель CodeCore

## 4.1 Каждый серьёзный запрос проходит через 6 стадий

1. `Classify`
2. `Select pipeline`
3. `Compose context`
4. `Execute actions`
5. `Verify outcome`
6. `Learn from result`

Если хотя бы одна стадия отсутствует, система деградирует в обычный чат.

## 4.2 Для длинных задач обязателен persistent handoff

Из лучших практик следует жёсткое правило: длинные задачи нельзя держать только в живом контексте.

CodeCore должен иметь persistent artifacts:

- `plan`;
- `handoff summary`;
- `verification status`;
- `open risks`;
- `rollback notes`.

Это может храниться в `.codecore/` и в memory store.

## 4.3 Exploration и execution должны быть отделены

Для сложных изменений нужны два режима:

- `plan/explore` — read-only анализ, декомпозиция, риски;
- `execute` — реальные изменения, tool calls, patching.

Это снижает число ложных правок и дорогостоящих заходов “не туда”.

## 4.4 Подагенты нужны, но строго по делу

Мультиагентность нужна только там, где есть реальная изоляция подзадач:

- planner vs coder;
- researcher vs modifier;
- reviewer vs executor.

CodeCore не должен поощрять хаотическую армию агентов без ясных ролей и merge discipline.

---

## 5. Context Engineering Policy для CodeCore

## 5.1 Контекст - это бюджет внимания

CodeCore должен считать контекст не “лимитом токенов”, а ограниченным ресурсом внимания модели.

Поэтому обязательны:

- token budgeting;
- relevance filtering;
- tool output truncation;
- stale context cleanup;
- preservation of constraints and architectural decisions.

## 5.2 Всегда хранить, что нельзя потерять

При compaction и summary система обязана сохранить:

- цель задачи;
- критерии завершения;
- ключевые архитектурные решения;
- активные ограничения и запреты;
- текущее состояние проверки;
- что уже пробовали и почему не сработало;
- незавершённые шаги.

## 5.3 Tool outputs должны проходить через сжатие

Сырые выводы команд часто убивают качество контекста.

Требования:

- большие stdout/stderr сохраняются как artifact;
- в основной контекст попадает краткое summary;
- при ошибке включаются только релевантные фрагменты;
- успешные массовые логи заменяются на короткий статус (`passed`, `failed`, `N tests`, `top error`).

## 5.4 Compaction должен быть incremental

Нельзя пересобирать весь контекст с нуля на каждом шаге.

Лучший режим для CodeCore:

- delta-updates;
- selective replacement устаревших фактов;
- summary batches вместо summary-per-message;
- handoff artifacts вне основного контекста.

## 5.5 `/clear` и `/compact` - это разные действия

Архитектурно нужно поддержать два режима:

- `clear` - полная очистка активной истории для новой задачи;
- `compact` - сжатие текущей задачи без потери хода работы.

Это разные операции и их нельзя смешивать.

---

## 6. Memory Policy для CodeCore

## 6.1 Память должна извлекать знания, а не просто хранить разговоры

В память попадает только то, что повышает будущую эффективность:

- устойчивые предпочтения;
- проверенные архитектурные решения;
- рабочие команды;
- типовые ошибки и успешные исправления;
- рейтинги моделей, skills, pipelines, MCP servers.

## 6.2 Memory write должен быть селективным

Не каждое сообщение достойно персистентной памяти.

Сохранять следует:

- decisions;
- outcomes;
- preferences;
- constraints;
- reusable patterns;
- failure signatures.

Не следует сохранять без фильтра:

- весь transcript;
- шумные tool outputs;
- одноразовые логи без ценности;
- промежуточные гипотезы без подтверждения.

## 6.3 Metadata-first memory обязательна

Каждая memory unit должна иметь метаданные:

- откуда появилась;
- при какой задаче;
- какой моделью была получена;
- с каким quality score;
- насколько свежа;
- стоит ли ей доверять.

Без этого memory превращается в мусорное озеро.

## 6.4 Vector memory не является стартовым требованием

Из массива best practice следует разумный вывод:

- сначала metadata index + summaries + heuristics;
- только потом vector search, если появится реальная проблема recall quality.

CodeCore не должен начинать с избыточного RAG-стека там, где хватает структурированной памяти.

---

## 7. Skills Policy для CodeCore

## 7.1 Skill - это пакет знаний и workflow

Для CodeCore skill должен включать:

- manifest;
- summary;
- activation triggers;
- workflow steps;
- constraints;
- stop conditions;
- optional scripts/resources/templates.

## 7.2 Progressive disclosure обязательно

Трёхуровневая модель должна быть встроена в дизайн:

1. metadata;
2. instructions;
3. resources/scripts on demand.

Это позволяет иметь большую базу skills без постоянного загрязнения контекста.

## 7.3 Skills должны быть измеримыми

Нужны метрики по skill:

- activation count;
- success rate;
- effect on retries;
- effect on review findings;
- token overhead;
- usefulness by task tag.

Если skill ухудшает качество или раздувает контекст без пользы, он должен понижаться в ранжировании.

## 7.4 Skills не должны подменять policies

Если правило должно соблюдаться всегда - это не skill.

Skills отвечают за:

- domain knowledge;
- workflow guidance;
- checklists;
- reusable task methods.

Policies и hooks отвечают за:

- hard enforcement;
- security;
- approvals;
- mandatory checks.

---

## 8. MCP Policy для CodeCore

## 8.1 MCP - это capability bus

CodeCore должен использовать MCP как унифицированный слой внешних возможностей:

- tools;
- resources;
- prompts;
- subscriptions;
- cross-tool discoverability.

## 8.2 Но MCP не должен раздувать fixed context overhead

Из практики видно, что избыток MCP servers быстро съедает контекст только своими schema definitions.

Требования:

- dynamic loading capabilities;
- отключение нерелевантных серверов;
- ranking по пользе и стоимости;
- lightweight discovery before full activation.

## 8.3 CLI-first там, где это проще и дешевле

Если локальный CLI:

- детерминирован;
- безопасен;
- легко проверяется;
- даёт меньше контекстного шума,

то он должен быть предпочтён MCP-обёртке.

Практическое правило для CodeCore:

- стандартные dev operations: чаще CLI;
- внешние сервисы и многократно переиспользуемые интеграции: чаще MCP.

## 8.4 Каждый MCP server должен иметь trust profile

Для каждого сервера система должна знать:

- transport;
- auth mode;
- side-effect risk;
- data sensitivity;
- historical reliability;
- usefulness by task type.

Без trust profile MCP-федерация становится дырой в governance.

---

## 9. Model and Runtime Policy для CodeCore

## 9.1 Provider-agnostic is non-negotiable

CodeCore должен одинаково работать с:

- cloud APIs;
- open-source models;
- local inference;
- OpenAI-compatible gateways;
- VPN/no-VPN сценариями.

Главная цель этого слоя - не просто “поддержать всех”, а сделать так, чтобы модель была сменным компонентом, а не архитектурным центром системы.

## 9.2 Выбор модели должен быть policy-driven

Модель выбирается не по хайпу, а по матрице:

- task fit;
- tool-use quality;
- context capacity;
- latency;
- cost;
- privacy;
- reliability;
- local availability.

При этом среда должна стремиться к **result normalization**:

- хорошие модели дают лучший ceiling;
- но базовый floor качества должен обеспечиваться архитектурой CodeCore;
- если модель слабее, система компенсирует это более строгим pipeline, лучшими skills, более узким контекстом и обязательной верификацией.

## 9.3 Hybrid runtime - норма, а не исключение

CodeCore должен проектироваться сразу под гибридные маршруты:

- planner в сильной reasoning-модели;
- coder в дешёвой/быстрой coding-модели;
- reviewer в отдельной модели;
- local fallback при недоступности облака.

## 9.4 Runtime должен уметь жить в ограничениях

Для реального мира нужны:

- fallback chains;
- degraded mode;
- offline/local mode;
- retry policies;
- cached routing decisions.

---

## 10. Verification and Evaluation Policy

## 10.1 Верификация - обязательный слой архитектуры

CodeCore не должен считать задачу завершённой, если нет evidence.

Обязательные классы проверки:

- static: format, lint, typecheck;
- runtime: tests, commands, sample scenario;
- review: automated findings + human review where needed;
- policy: security, permissions, forbidden changes.

## 10.2 Evidence-driven outcome

Каждый результат должен иметь след:

- какой diff предложен;
- какие команды запускались;
- что прошло;
- что не прошло;
- что осталось непроверенным.

## 10.3 LLM-as-judge допустим, но не как единственный судья

Оценочные модели полезны для:

- comparative ranking;
- review support;
- style/quality heuristics.

Но они не заменяют:

- тесты;
- реальные запуски;
- deterministic checks.

## 10.4 Система должна учиться на outcomes

Нужно считать как минимум:

- success rate;
- retry count;
- patch acceptance;
- test pass rate;
- user rating;
- cost per successful task;
- skill effectiveness;
- MCP usefulness;
- provider reliability.

Без этих метрик self-improving architecture не состоится.

---

## 11. Security and Governance Policy

## 11.1 Security - часть runtime, а не внешний фильтр

Безопасность должна быть встроена в архитектуру CodeCore на уровне:

- input filtering;
- tool permissions;
- approval gates;
- secret handling;
- audit log;
- anomaly detection.

## 11.2 Least privilege по умолчанию

Каждый tool/MCP integration должен стартовать с минимальными правами.

По умолчанию:

- read-only лучше write;
- workspace write лучше destructive;
- явный approval лучше implicit trust.

## 11.3 Prompt injection считается базовой угрозой

CodeCore должен предполагать, что вредоносные инструкции могут прийти из:

- user input;
- документов;
- web pages;
- API responses;
- MCP resources;
- tool outputs.

Следствия:

- строгая граница между system / user / external content;
- sanitization внешних данных;
- classification подозрительных запросов;
- separate treatment for untrusted resources.

## 11.4 Secrets никогда не живут в prompt

Секреты должны храниться только в secret stores / env / secure runtime.

Запрещается:

- встраивать ключи в системные промпты;
- логировать полные секреты;
- сохранять секретные фрагменты в memory/events/artifacts без маскировки.

## 11.5 High-impact actions требуют approval gates

Обязательное подтверждение для:

- destructive file ops;
- production deploys;
- write в production DB;
- внешних side effects;
- mass-edit actions с большим blast radius.

---

## 12. Git, Parallelism, and Change Management

## 12.1 Параллельные агенты требуют изоляции

Лучший практический паттерн - worktree isolation.

CodeCore должен поддерживать:

- отдельные execution contexts;
- отдельные ветки/worktrees;
- diff visibility;
- merge discipline;
- explicit ownership of changed files.

## 12.2 Малые шаги лучше больших заходов

Изменения должны быть:

- короткими;
- проверяемыми;
- обратимыми;
- связанными с одной подзадачей.

## 12.3 Нужна строгая traceability изменений

Для каждого change set нужно знать:

- какой запрос его породил;
- какой pipeline его выполнил;
- какие файлы затронуты;
- какие проверки прошли;
- можно ли откатить.

---

## 13. Антипаттерны, которые CodeCore НЕ должен интегрировать

Ниже список вещей, которые нужно сознательно отбрасывать.

### 13.1 Монолитный вечный промпт

Плохо:

- запихнуть весь проектный опыт, правила, навыки и историю в один гигантский системный prompt.

Почему вредно:

- растит fixed overhead;
- снижает compliance;
- размывает важные инструкции;
- ломает масштабируемость.

### 13.2 “Одна модель решит всё”

Плохо:

- делать архитектуру вокруг любимой модели или одного провайдера.

Почему вредно:

- vendor lock-in;
- нет fallback;
- нельзя адаптировать cost/latency/privacy;
- ломается при блокировках, лимитах, деградации провайдера.

И главное: это мешает строить саму среду. Вместо инженерной машины получается культ конкретного движка.

### 13.3 Бесконечный transcript как память

Плохо:

- считать, что chat history и есть память.

Почему вредно:

- растёт шум;
- нет recall discipline;
- нельзя строить learning loops;
- ухудшается качество и растёт цена.

### 13.4 MCP everywhere

Плохо:

- заворачивать любую мелочь в MCP даже там, где обычный CLI лучше.

Почему вредно:

- перегружает контекст схемами инструментов;
- усложняет систему без пользы;
- увеличивает attack surface.

### 13.5 YOLO automation

Плохо:

- безусловный auto-approval для всех действий.

Почему вредно:

- высокий риск разрушительных действий;
- отсутствие контроля blast radius;
- архитектура перестает быть production-grade.

### 13.6 Автокомпакт без сохранения rationale

Плохо:

- сжимать историю так, что исчезают решения, ограничения и причины прошлых шагов.

Почему вредно:

- появляется повтор работы;
- агент забывает, почему было выбрано именно это решение;
- ломается long-running execution.

### 13.7 Хранить сырой tool noise в основном контексте

Плохо:

- бесконтрольно подмешивать большие логи, grep outputs, diff dumps, tree listings.

Почему вредно:

- контекст переполняется мусором;
- падает точность следующих шагов;
- растёт cost без пользы.

### 13.8 Смешивать roles в одном агенте без явной границы

Плохо:

- один и тот же runtime одновременно исследует, планирует, пишет, ревьюит и принимает результат без отдельных этапов.

Почему вредно:

- self-confirmation bias;
- трудно локализовать ошибку;
- плохая explainability.

### 13.9 Skills как папка случайных markdown-файлов

Плохо:

- хранить skills без manifest, triggers, metrics и структуры.

Почему вредно:

- агент не понимает, когда skill нужен;
- нет измеримости;
- нет масштабирования.

### 13.10 Security как “потом добавим”

Плохо:

- сначала дать агенту все возможности, потом поверх навесить фильтры.

Почему вредно:

- привилегии уже разданы;
- архитектура не audit-friendly;
- prompt injection/tool abuse становятся системными, а не локальными проблемами.

### 13.11 Vector DB first

Плохо:

- начинать с тяжёлого RAG/vector стека без доказанной необходимости.

Почему вредно:

- избыточная сложность;
- больше инфраструктуры, чем пользы;
- не решает проблемы плохой taxonomy и плохих metadata.

### 13.12 Автослияние без review/evidence

Плохо:

- считать задачу выполненной только потому, что модель внесла изменения.

Почему вредно:

- нет подтверждения качества;
- ломается доверие к системе;
- теряется production пригодность.

---

## 14. Практические выводы для ближайшей реализации CodeCore

В ближайших версиях архитектура должна обеспечить следующие обязательные свойства.

### v0.1-v0.2

- REPL с явным session state;
- provider broker с fallback;
- context manager с token budget;
- skill loader с progressive disclosure;
- structured telemetry;
- verification hooks;
- project contract (`.codecore/project.yaml` или аналог).

### v0.3-v0.4

- outcome-driven rankings;
- memory taxonomy + selective recall;
- `/stats` и route ranking;
- compaction/handoff strategy;
- execution summaries вместо сырого tool noise;
- approval policy engine.

### v0.5+

- multi-agent role orchestration;
- MCP federation with trust scoring;
- comparative evaluation pipelines;
- adaptive route optimization;
- richer project/global memory.

---

## 15. Архитектурная позиция

CodeCore должен вобрать лучшие практики LLM-driven разработки не как набор советов, а как **свойства системы**.

То есть:

- spec-driven не как привычка пользователя, а как supported workflow;
- verification не как совет, а как runtime layer;
- memory не как transcript, а как metadata architecture;
- skills не как markdown, а как executable knowledge modules;
- MCP не как мода, а как capability bus под governance;
- self-improvement не как лозунг, а как telemetry + ranking + adaptation.

Если это соблюдено, CodeCore станет не оболочкой вокруг моделей, а действительно развивающимся домом для инженерных агентов.

---

## 16. Source Basis

Концентрат основан прежде всего на этих материалах массива:

- `docs/best_practice/01_foundations/lesson_01_agent_loop.md`
- `docs/best_practice/01_foundations/lesson_03_ai_engineering.md`
- `docs/best_practice/02_methodology/lesson_01_sdd.md`
- `docs/best_practice/02_methodology/lesson_03_practices.md`
- `docs/best_practice/03_context_engineering/lesson_01_context_editing_compaction.md`
- `docs/best_practice/03_context_engineering/lesson_02_memory_systems.md`
- `docs/best_practice/04_skills/lesson_01_skills_overview.md`
- `docs/best_practice/04_skills/lesson_03_skills_context_engineering.md`
- `docs/best_practice/05_agents_mcp/lesson_01_mcp_protocol.md`
- `docs/best_practice/05_agents_mcp/lesson_04_mcp_practice.md`
- `docs/best_practice/07_security/lesson_01_threats.md`
- `docs/best_practice/07_security/lesson_02_guardrails.md`
- `docs/best_practice/09_models/lesson_02_local_cloud_runtime.md`
- `docs/best_practice/10_tooling/lesson_02_best_practices.md`
- `docs/best_practice/10_tooling/lesson_03_engineer_practice.md`
- `docs/best_practice/11_capstone/lesson_02_capstone_rubric.md`
