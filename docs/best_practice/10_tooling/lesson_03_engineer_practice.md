---
module: "10_tooling"
lesson: 3
title: "Инженерные практики работы с Claude Code"
type: "practice"
prerequisites: ["10_tooling/lesson_02"]
difficulty: "advanced"
tags: ["engineering", "advanced", "verification", "workflow", "practice"]
---

# Инженерные практики работы с Claude Code

Этот урок предназначен для инженеров, которые уже используют Claude Code и хотят workflow, который будет более предсказуемым, более контролируемым и более верифицируемым.

Материал основан на переводе китайской статьи, получившей 6000+ лайков в developer community, и отражает шесть месяцев интенсивного использования Claude Code (~$40/месяц на два аккаунта). Ключевой инсайт: проблемы с Claude Code — это не prompt-engineering problem, а **systems-design problem**.

---

## 1. Шестислойная модель Claude Code

Claude Code — это не просто chat interface. Это итеративный агентский цикл с шестью слоями, каждый из которых нужно понимать и контролировать:

```
Layer 1: CLAUDE.md        — Project contract
Layer 2: Rules            — Path/language-specific constraints
Layer 3: Skills           — On-demand workflows
Layer 4: Tools / MCP      — Actions and capabilities
Layer 5: Hooks            — Deterministic automation
Layer 6: Subagents        — Isolated execution
```

**Критический принцип:** over-index на одном слое — и система становится нестабильной:
- CLAUDE.md слишком длинный → загрязняет собственный контекст
- Слишком много tools → noisy selection
- Слишком много subagents → drift состояния сложнее контролировать
- Пропуск verification → невозможно определить, где произошла ошибка

---

## 2. Execution Model — как Claude Code реально работает

### 2.1. Итеративный agent loop

```
Gather context → Take action → Verify result → [Done or loop back]
     ↑                    ↓
  CLAUDE.md          Hooks / Permissions / Sandbox
  Skills             Tools / MCP
  Memory
```

После длительного использования становится очевидно: failures обычно происходят не от недостатка raw model capability. **Wrong information опаснее, чем missing information.** Часто реальная проблема в том, что что-то было произведено, но нет надёжного способа его валидировать или откатить.

### 2.2. Пять поверхностей, которые реально имеют значение

Когда что-то идёт не так, проверяйте эти поверхности в первую очередь:

| Поверхность | Что проверять |
|-------------|---------------|
| Context loading | Порядок загрузки контекста (прежде чем винить модель) |
| Control layer | Permissions, hooks, sandbox (прежде чем винить агента за "гиперактивность") |
| Context quality | Intermediate artifacts в контексте (если quality падает в длинных сессиях) |
| Tool selection | Правильный ли tool выбран для задачи |
| Verification | Есть ли способ проверить результат |

**Если результаты нестабильны** → inspect context loading order.
**Если автоматизация заходит слишком далеко** → inspect control layer.
**Если качество падает в длинных сессиях** → assume intermediate artifacts загрязнили контекст, consider fresh session.

---

## 3. Concept Boundaries: чёткое разделение компонентов

### 3.1. Простое правило

| Компонент | Назначение |
|-----------|-----------|
| **Tools / MCP** | Дать Claude новые действия (write, read, query) |
| **Skills** | Предоставить reusable методы и workflows |
| **Subagents** | Изолировать execution (свой контекст, свои tools) |
| **Hooks** | Enforcing constraints + audit signals (deterministic) |
| **Plugins** | Distribution и packaging |

**Размытие этих границ** делает систему трудной для reasoning. Если skill имеет side effects, которые должны быть deterministic — это hook. Если hook требует multi-step reasoning — это skill или subagent.

### 3.2. Разница между CLAUDE.md, Rules, Skills

```
CLAUDE.md   → Always loaded   → Project contract
Rules       → Path-loaded     → Language/directory specific
Skills      → On-demand       → Workflows and domain knowledge
```

**Нарушение:** положить всё в CLAUDE.md → файл раздувается, compliance падает, контекст загрязняется. Разделите по принципу: "как часто это нужно" и "для каких файлов это релевантно".

---

## 4. Context Engineering — главное системное ограничение

### 4.1. Реальная структура стоимости контекста

Многие думают о контексте как о "capacity problem", но реальная проблема — **noise**: полезная информация утоплена в нерелевантном контенте.

```
200K total context
├── Fixed overhead (~15-20K)
│   ├── System instructions: ~2K
│   ├── All enabled Skill descriptors: ~1-5K
│   ├── MCP Server tool definitions: ~10-20K  ← Largest hidden overhead
│   └── LSP state: ~2-5K
│
├── Semi-fixed (~5-10K)
│   ├── CLAUDE.md: ~2-5K
│   └── Memory: ~1-2K
│
└── Dynamically available (~160-180K)
    ├── Conversation history
    ├── File contents
    └── Tool call results
```

**Пример:** один MCP-сервер вроде GitHub может экспонировать 20-30 tool definitions по ~200 tokens каждый = 4,000-6,000 tokens. Подключите 5 серверов — ~25,000 tokens (12.5%) на fixed overhead.

### 4.2. Рекомендуемое послойное размещение контекста

```
Always resident    → CLAUDE.md: project contract / build commands / prohibitions
Path-loaded        → rules: language / directory / file-type specific
On-demand loaded   → skills: workflows / domain knowledge
Isolated loaded    → subagents: heavy exploration / parallel research
Never in context   → hooks: deterministic scripts / audit / blocking
```

### 4.3. Context Best Practices

1. **CLAUDE.md — короткий, строгий, операционный.** Приоритет: commands, constraints, architectural boundaries. В примерах Anthropic эти файлы достаточно компактны.

2. **Большие reference documents** → в supporting files для skill, НЕ напрямую в SKILL.md.

3. **`.claude/rules/`** для path- и language-specific правил. Root CLAUDE.md не должен обрабатывать каждую вариацию.

4. **`/context` проактивно** для инспекции потребления. Не ждите автоматической компрессии.

5. **Переключение задач** → `/clear`. **Новая фаза той же задачи** → `/compact`.

6. **Compact Instructions в CLAUDE.md** — вы решаете, что переживает компрессию, а не алгоритм.

### 4.4. Tool Output Noise — скрытый killer контекста

Динамический контекст имеет собственную ловушку: **tool output**. Один запуск `cargo test` может произвести тысячи строк. `git log` заполняется быстро. `find` или `grep` легко flood-ят окно нерелевантными совпадениями.

Claude не нуждается во всём этом, но раз попав в контекст, данные потребляют реальные токены и crowd out conversation history.

**Решение: RTK (Rust Token Killer)** — фильтрация command output до попадания в Claude:

```
# Raw output, который Claude увидит
running 262 tests
test auth::test_login ... ok
...（тысячи строк）

# После RTK
✓ cargo test: 262 passed (1 suite, 0.08s)
```

Claude реально нужно только: "прошло ли, и если нет — где упало". Всё остальное — noise. RTK перезаписывает команды transparently через hook.

**Быстрая альтернатива:** `| head -30` как ручная truncation.

### 4.5. Ловушка компрессии (The Compression Trap)

Алгоритм компрессии по умолчанию оптимизирует для "re-readability". Early tool outputs и file contents часто удаляются первыми — вместе с ними уходят **architectural decisions и constraint rationale**.

Два часа спустя, когда нужно что-то изменить — ранние решения уже потеряны. Удивительно много багов начинается именно здесь.

**Решение: Compact Instructions в CLAUDE.md:**

```markdown
## Compact Instructions

When compressing, preserve in priority order:

1. Architecture decisions (NEVER summarize)
2. Modified files and their key changes
3. Current verification status (pass/fail)
4. Open TODOs and rollback notes
5. Tool outputs (can delete, keep pass/fail only)
```

### 4.6. HANDOFF.md — надёжнее, чем Compact Instructions

Перед завершением сессии попросите Claude записать текущее состояние:

> Write the current progress in HANDOFF.md. Explain what you tried, what worked, what didn't, so the next agent with fresh context can continue from just this file.

Review быстро на пропуски. Следующая сессия начинается с HANDOFF.md вместо зависимости от качества компрессии.

### 4.7. Plan Mode — инженерная ценность

Plan Mode разделяет exploration и execution:

- **Exploration phase** — read-only
- Claude может уточнить goals и boundaries до предложения плана
- **Execution** начинается только после подтверждения плана

Для complex refactors, migrations, cross-module changes это разделение обычно лучше, чем немедленное редактирование. Running with a bad assumption гораздо менее вероятен, когда план подтверждён.

**Double-tap `Shift+Tab`** для входа в Plan Mode. Полезный паттерн: один agent drafts план, другой review-ит перед execution.

---

## 5. Skills Design — workflow packages, не template library

### 5.1. Что такое skills на самом деле

Skills — это **on-demand workflow packages**. Их descriptors остаются в контексте, а полное body загружается только когда нужно. Операционно это отличается от saved prompts.

### 5.2. Что делает skill хорошим

1. **Description** говорит модели **когда** использовать skill, а не только что он содержит
2. Определяет **complete steps**: inputs, outputs, stop conditions — не только opening instruction
3. Body содержит **navigation и core constraints** only; large reference material в supporting files
4. Skills с side effects — **explicitly disable model invocation**; иначе модель сама решает, запускать ли

### 5.3. Progressive Disclosure — on-demand loading

Не показывайте модели всё сразу. Дайте index и navigation, затем загружайте детали по запросу:

- `SKILL.md` — task semantics, boundaries, execution skeleton
- Supporting files — domain details
- Scripts — deterministic context gathering

**Stable structure:**

```
.claude/skills/
└── incident-triage/
    ├── SKILL.md
    ├── runbook.md
    ├── examples.md
    └── scripts/
        └── collect-context.sh
```

### 5.4. Три типичных типа skills

#### Type 1: Checklist (Quality Gate)

Запускается перед release, чтобы ничего критического не было пропущено:

```yaml
---
name: release-check
description: Use before cutting a release to verify build, version, and smoke test.
---

## Pre-flight (All must pass)
- [ ] `cargo build --release` passes
- [ ] `cargo clippy -- -D warnings` clean
- [ ] Version bumped in Cargo.toml
- [ ] CHANGELOG updated
- [ ] `kaku doctor` passes on clean env

## Output
Pass / Fail per item. Any Fail must be fixed before release.
```

#### Type 2: Workflow (Standardized Operations)

Config migration — high risk, поэтому explicit invocation и built-in rollback:

```yaml
name: config-migration
description: Migrate config schema. Run only when explicitly requested.
disable-model-invocation: true
---

## Steps
1. Backup: `cp ~/.config/kaku/config.toml ~/.config/kaku/config.toml.bak`
2. Dry run: `kaku config migrate --dry-run`
3. Apply: remove `--dry-run` after confirming output
4. Verify: `kaku doctor` all pass

## Rollback
`cp ~/.config/kaku/config.toml.bak ~/.config/kaku/config.toml`
```

#### Type 3: Domain Expert (Encapsulated Decision Framework)

При runtime issues Claude собирает evidence по фиксированному пути, а не угадывает:

```yaml
---
name: runtime-diagnosis
description: Use when kaku crashes, hangs, or behaves unexpectedly at runtime.
---

## Evidence Collection
1. Run `kaku doctor` and capture full output
2. Last 50 lines of `~/.local/share/kaku/logs/`
3. Plugin state: `kaku --list-plugins`

## Decision Matrix
| Symptom | First Check |
|---|---|
| Crash on startup | doctor output → Lua syntax error |
| Rendering glitch | GPU backend / terminal capability |
| Config not applied | Config path + schema version |

## Output Format
Root cause / Blast radius / Fix steps / Verification command
```

### 5.5. Держите descriptors короткими

Каждый enabled skill держит descriptor в контексте. Разница между оптимизированным и неоптимизированным огромна:

```yaml
# Inefficient (~45 tokens)
description: |
  This skill helps you review code changes in Rust projects.
  It checks for common issues like unsafe code, error handling...
  Use this when you want to ensure code quality before merging.

# Efficient (~9 tokens)
description: Use for PR reviews with focus on correctness.
```

**Стратегия invocation по частоте:**

| Частота | Стратегия |
|---------|-----------|
| High (>1/session) | Keep auto-invoke, optimize descriptor |
| Low (<1/session) | Disable auto-invoke, trigger manually |
| Very low (<1/month) | Remove skill, document in AGENTS.md |

### 5.6. Skills Anti-Patterns

- Description слишком короткий: `description: help with backend` (срабатывает для почти любой backend задачи)
- Body слишком длинный: сотни строк manual content в SKILL.md
- Один skill покрывает review, deploy, debug, docs, incident — пять разных вещей
- Side-effect skills разрешающие model auto-invocation

---

## 6. Tool Design — помочь Claude выбрать правильный tool

### 6.1. Tools для Claude ≠ APIs для людей

Human-facing APIs оптимизируют для feature completeness. Agent-facing tools должны оптимизировать для **correct selection и correct use**.

### 6.2. Практические принципы дизайна

1. **Prefix names** по system или resource layer: `github_pr_*`, `jira_issue_*`
2. **Support `response_format`**: concise / detailed для больших ответов
3. **Error responses** должны быть corrective — не opaque codes only
4. **Merge high-level task tools** — не экспонируйте слишком много low-level fragments
5. **Avoid `list_all_*`** patterns, которые заставляют модель самостоятельно фильтровать результаты

### 6.3. Уроки из эволюции internal tools Claude Code

#### AskUserQuestion — три версии

Проблема: agent должен остановиться и спросить пользователя вопрос.

| Версия | Подход | Результат |
|--------|--------|-----------|
| V1 | Question parameter в существующих tools (Bash) | Claude часто игнорирует parameter, продолжает без паузы |
| V2 | Specific markdown format, parsed outer layer | Нет hard enforcement, questioning path fragile |
| V3 | **Standalone AskUserQuestion tool** | Надёжно: tool call = pause signal |

**Практический вывод:** если хотите, чтобы Claude остановился и спросил — дайте dedicated tool. Flags и output-format conventions гораздо легче для модели пропустить.

#### Todo Tool — эволюция

Ранние версии использовали TodoWrite + периодические reminders. С улучшением моделей инструмент стал больше constraint, чем benefit.

**Урок:** контроли, полезные для слабых моделей, могут стать ненужным friction позже. Периодически пересматривайте.

#### Search Tool — от RAG к Grep

Ранние подходы: RAG-style vector database. Быстро, но требует индексации, fragile across environments, плохое adoption моделью.

**Решение:** Grep-style tool, позволяющий Claude искать напрямую. Side effect: Claude может читать skill file, следовать references к другим файлам и загружать информацию рекурсивно по необходимости — **progressive disclosure** в действии.

### 6.4. Когда НЕ добавлять ещё один tool

- Задача, которую local shell уже выполняет надёжно
- Модели нужно static knowledge, а не external interaction
- Requirements лучше подходят для skill workflow, чем tool actions
- Description, schema и return format ещё не стабилизированы для использования моделью

---

## 7. Hooks — запуск вашего кода до/после действий Claude

### 7.1. Hooks — это не "автоматические скрипты"

Hooks лучше понимать как способ **вынести работу из on-the-fly model judgment в deterministic processes**: форматирование, защита файлов, нотификации — это не то, что стоит полагаться на модель помнить каждый раз.

### 7.2. Hook Points

| Hook | Когда срабатывает |
|------|-------------------|
| `PreToolUse` | До выполнения tool — блокировка, валидация |
| `PostToolUse` | После выполнения tool — formatting, lint, check |
| `SessionStart` | При старте сессии — inject dynamic context |
| `Notification` | При компрессии или других events — re-inject context |
| `Stop` | При завершении response — notification, audit |

### 7.3. Что подходит и не подходит для hooks

**Подходит:**
- Blocking модификации protected files
- Auto formatting/lint/light validation после Edit
- Injection dynamic context после SessionStart (Git branch, env vars)
- Push notifications после task completion

**Не подходит:**
- Complex semantic judgments требующие много контекста
- Long-running business processes
- Decisions требующие multi-step reasoning и tradeoffs → используйте skills или subagents

### 7.4. Практический пример: mixed-language project

Два языка — два checks, каждый по file type:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "pattern": "*.rs",
        "hooks": [{
          "type": "command",
          "command": "cargo check 2>&1 | head -30",
          "statusMessage": "Running cargo check..."
        }]
      },
      {
        "matcher": "Edit",
        "pattern": "*.lua",
        "hooks": [{
          "type": "command",
          "command": "luajit -b $FILE /dev/null 2>&1 | head -10",
          "statusMessage": "Checking Lua syntax..."
        }]
      }
    ],
    "Notification": [
      {
        "type": "command",
        "command": "osascript -e 'display notification \"Task completed\" with title \"Claude Code\"'"
      }
    ]
  }
}
```

### 7.5. Раннее обнаружение ошибок экономит время

В сессии на 100 edits, экономия 30-60 секунд на каждом → **1-2 часа суммарно**. Это material.

**Важно:** ограничивайте длину output (`| head -30`), чтобы hook output не загрязнял контекст.

### 7.6. Трёхслойный стек: Hooks + Skills + CLAUDE.md

| Слой | Роль | Пример |
|------|------|--------|
| CLAUDE.md | Declare | "Must pass tests and lint before commit" |
| Skill | Instruct | В каком порядке запускать тесты, как читать failures, как fix-ить |
| Hook | Enforce | Hard validation на critical paths, block если нужно |

**На практике любой один слой имеет gaps:**
- CLAUDE.md rules alone → игнорируются
- Hooks alone → не могут handle judgment calls
- **Все три вместе** — то, что реально работает

---

## 8. Subagents — изолированное выполнение

### 8.1. Основная ценность — isolation, не parallelism

Subagent — независимый Claude instance с собственным context window и только разрешёнными tools. Codebase scans, test runs, review passes генерирующие большой output идут в subagent, а main thread получает только summary.

### 8.2. Встроенные типы

| Тип | Описание |
|-----|----------|
| **Explore** | Read-only scan, Haiku для экономии |
| **Plan** | Planning research |
| **General-purpose** | Общий |
| **Custom** | Настраиваемый (.claude/agents/) |

### 8.3. Explicit Constraints в конфигурации

- **tools / disallowedTools** — ограничьте доступные tools; не давайте те же broad permissions, что и main thread
- **model** — exploration tasks → Haiku/Sonnet, important reviews → Opus
- **maxTurns** — предотвратить runaway
- **isolation: worktree** — изолировать filesystem при модификации файлов

### 8.4. Background execution

Долгие bash-команды можно отправить в background через `Ctrl+B`. Claude проверит результаты позже через BashOutput tool, не блокируя main thread.

### 8.5. Anti-Patterns subagents

| Anti-Pattern | Проблема |
|--------------|----------|
| Те же broad permissions, что и main thread | Isolation бессмысленна |
| Output format не зафиксирован | Main thread не может использовать результат |
| Сильные зависимости между subtasks | Frequent sharing intermediate state — subagent не подходит |

---

## 9. Prompt Caching — first-class design constraint

### 9.1. Caching — не просто cost optimization

Prompt caching **формирует архитектуру**. Высокий cache hit rate:
- Снижает стоимость
- Улучшает latency
- Делает практичными более generous rate limits

### 9.2. Prompt Layout для caching

Prompt caching работает через prefix matching — контент от начала запроса до каждого `cache_control` breakpoint кешируется. **Порядок имеет значение:**

```
1. System Prompt    → Static, locked
2. Tool Definitions → Static, locked
3. Chat History     → Dynamic, comes after
4. Current input    → Last
```

### 9.3. Типичные ошибки caching

| Ошибка | Почему плохо |
|--------|-------------|
| Timestamped content в system prompt | Меняется каждый раз → cache miss |
| Non-deterministic shuffling tool definitions | Порядок меняется → cache invalidation |
| Adding/removing tools mid-session | Ломает prefix matching |
| Dynamic info (current time) в system prompt | Ставьте в later message |

### 9.4. Не переключайте модели mid-session

Prompt cache **model-specific**. Если вы проговорили 100K tokens с Opus и хотите задать простой вопрос, переключение на Haiku **дороже**, чем продолжение с Opus — потому что нужно перестроить весь cache для Haiku.

**Если нужно переключить:** hand off через subagent — Opus подготавливает "handoff message" для другой модели.

### 9.5. Compaction под капотом

Когда context window близок к заполнению:
1. Claude Code fork-ает summarization call над существующим разговором (может benefit от caching)
2. Много turns сжимаются в shorter summary
3. System prompt, tool definitions и referenced files остаются
4. Освобождается пространство для продолжения сессии

### 9.6. Plan Mode и cache stability

На первый взгляд Plan Mode должен переключать на другой read-only toolset. Но это повредит cache reuse. Вместо этого Anthropic использует tool-driven approach: модель может войти в plan mode без смены underlying tool prefix → cache stability сохраняется.

### 9.7. defer_loading — lazy loading для tools

Много MCP tools → включение каждого full definition в каждый запрос дорого. Добавление/удаление tools mid-session тоже вредит cache. Подход: lightweight stubs в stable prefix, fuller schemas загружаются только когда модель их выбирает.

---

## 10. Verification Loop — без верификатора нет engineering agent

### 10.1. "Claude says it's done" — не имеет инженерной ценности

Что имеет значение:
- Действительно ли это корректно?
- Можно ли откатить, если что-то не так?
- Auditable ли процесс?

### 10.2. Уровни верификации

| Уровень | Инструменты |
|---------|-------------|
| **Lowest** | Command exit codes, lint, typecheck, unit test |
| **Middle** | Integration tests, screenshot comparison, contract test, smoke test |
| **Higher** | Production log verification, monitoring metrics, manual review checklists |

### 10.3. Explicit verification в Prompt, Skill и CLAUDE.md

```markdown
## Verification

For backend changes:
- Run `make test` and `make lint`
- For API changes, update contract tests under `tests/contracts/`

For UI changes:
- Capture before/after screenshots if visual

Definition of done:
- All tests pass
- Lint passes
- No TODO left behind unless explicitly tracked
```

### 10.4. Простой тест

> Если вы не можете чётко объяснить "как Claude знает, что он закончил правильно" — задача, вероятно, не подходит для автономного выполнения Claude.

Без acceptance criteria нет reliable notion of a correct answer, независимо от capability модели.

---

## 11. Часто используемые команды

### 11.1. Context Management

```bash
/context   # Inspect token consumption, включая MCP и file-read ratios
/clear     # Reset session; полезно когда один и тот же issue уже corrected дважды
/compact   # Compress с сохранением key points; лучше работает с Compact Instructions
/memory    # Confirm какой CLAUDE.md реально загрузился
```

### 11.2. Capabilities и Governance

```bash
/mcp           # Manage MCP connections, check token costs, disconnect idle servers
/hooks         # Manage hooks — key control-plane entry point
/permissions   # View or update permission whitelist
/sandbox       # Configure sandbox isolation
/model         # Switch: Opus (deep reasoning), Sonnet (routine), Haiku (quick exploration)
```

### 11.3. Session Continuity и Parallelism

```bash
claude --continue               # Resume latest session
claude --resume                 # Open selector for historical sessions
claude --continue --fork        # Fork from existing session
claude --worktree               # Create isolated git worktree
claude -p "prompt"              # Non-interactive mode (CI, pre-commit, scripts)
claude -p --output-format json  # Structured output for scripts
```

### 11.4. Менее известные, но полезные команды

| Команда | Назначение |
|---------|-----------|
| `/simplify` | Quick pass над recently modified code: reuse, quality, efficiency |
| `/rewind` | Возврат к checkpoint + new summary (не "undo") |
| `/btw` | Quick side question без прерывания main task |
| `/insight` | Анализ текущей сессии → что кодифицировать в CLAUDE.md |
| `stream-json` | `claude -p --output-format stream-json` — real-time JSON event stream |
| `Double-tap ESC` | Вернуть предыдущий input для редактирования |

### 11.5. Conversation history — всё локально

Session records хранятся в `~/.claude/projects/`. Folder names derived from project path. Каждая сессия — `.jsonl` файл.

```bash
grep -rl "keyword" ~/.claude/projects/
```

Или попросите Claude поискать в предыдущих обсуждениях по теме.

---

## 12. Как написать хороший CLAUDE.md

### 12.1. CLAUDE.md — collaboration contract

Не team documentation. Не knowledge base. Только информация, которая **должна действовать в каждой сессии**.

**Начните с ничего.** Используйте Claude Code, затем добавляйте записи только когда замечаете, что повторяете одну и ту же инструкцию. Для добавления: `#` для append текущего разговора в CLAUDE.md, или скажите "add this to the project's CLAUDE.md".

### 12.2. Что включать

| Категория | Примеры |
|-----------|---------|
| Build/test/lint/run commands | `pnpm install`, `pnpm test`, `pnpm lint` |
| Key directory structure | Module boundaries |
| Code style и naming constraints | Explicit, не vague |
| Non-obvious environment dependencies | Pitfalls |
| Prohibitions (NEVER list) | High-risk operations |
| Compact Instructions | Что должно пережить компрессию |

### 12.3. Что НЕ включать

- Длинные background introductions
- Полная API documentation
- Vague principles ("write high-quality code")
- Очевидное, что Claude может вывести из чтения repo
- Большие background materials (→ skills)

### 12.4. High-Quality Template

```markdown
# Project Contract

## Build And Test
- Install: `pnpm install`
- Dev: `pnpm dev`
- Test: `pnpm test`
- Typecheck: `pnpm typecheck`
- Lint: `pnpm lint`

## Architecture Boundaries
- HTTP handlers live in `src/http/handlers/`
- Domain logic lives in `src/domain/`
- Do not put persistence logic in handlers
- Shared types live in `src/contracts/`

## Coding Conventions
- Prefer pure functions in domain layer
- Do not introduce new global state without explicit justification
- Reuse existing error types from `src/errors/`

## Safety Rails

## NEVER
- Modify `.env`, lockfiles, or CI secrets without explicit approval
- Remove feature flags without searching all call sites
- Commit without running tests

## ALWAYS
- Show diff before committing
- Update CHANGELOG for user-facing changes

## Verification
- Backend changes: `make test` + `make lint`
- API changes: update contract tests under `tests/contracts/`
- UI changes: capture before/after screenshots

## Compact Instructions
Preserve:
1. Architecture decisions (NEVER summarize)
2. Modified files and key changes
3. Current verification status (pass/fail commands)
4. Open risks, TODOs, rollback notes
```

### 12.5. Пусть Claude поддерживает свой CLAUDE.md

Полезная привычка — обновлять CLAUDE.md сразу после коррекции ошибки:

> Update your CLAUDE.md so you don't make that mistake again.

Claude достаточно хорошо пишет правила для себя. Но периодически review-ите файл — записи устаревают, и constraints, которые когда-то помогали, могут перестать быть оправданными.

---

## 13. Полевые заметки из реального проекта

### 13.1. "Environment Transparency" важнее, чем вы думаете

Claude Code вызывает реальные shells, git, package managers, локальные конфигурации. Если один layer непрозрачен — Claude начинает гадать. Как только он начинает гадать об environment — reliability обычно падает быстро.

**Решение:** `doctor` command, который собирает environment state, dependencies, configuration status в structured health report. Запуск перед работой Claude Code eliminates cases, где агент начинает с неправильного понимания environment.

**Вывод:** когда CLI экспонирует semantically clear subcommands (`init`, `config`, `reset`), Claude Code использует их надёжнее, чем когда ему нужно infer, где лежат configuration files. **Converge state first, then expose edit entry points.**

### 13.2. Complete Engineering Layout Reference

Reference structure для полной Claude Code setup в проекте:

```
Project/
├── CLAUDE.md
├── .claude/
│   ├── rules/
│   │   ├── core.md
│   │   ├── config.md
│   │   └── release.md
│   ├── skills/
│   │   ├── runtime-diagnosis/     # Collect logs, state, dependencies
│   │   ├── config-migration/      # Config migration + rollback
│   │   ├── release-check/         # Pre-release validation
│   │   └── incident-triage/       # Production incident triage
│   ├── agents/
│   │   ├── reviewer.md
│   │   └── explorer.md
│   └── settings.json
└── docs/
    └── ai/
        ├── architecture.md
        └── release-runbook.md
```

С global constraints (CLAUDE.md), path constraints (rules), workflows (skills) и deeper architectural detail, разделёнными чисто, Claude Code ведёт себя **значительно более предсказуемо**.

**Для нескольких проектов:** стабильные personal defaults в `~/.claude/`, project-specific differences в каждом `.claude/` проекта.

---

## 14. Common Anti-Patterns

| Anti-Pattern | Проблема | Решение |
|-------------|----------|---------|
| CLAUDE.md на 500+ строк | Compliance падает, noise доминирует | Split в rules + skills, litmus test каждой строки |
| Все tools разрешены всем subagents | Isolation бессмысленна | Explicit tools/disallowedTools per agent |
| Skills с vague descriptions | Trigger для любой задачи | Description = когда использовать, не что содержит |
| One skill = five workflows | Невозможно target invocation | Один skill = одна задача |
| Нет Compact Instructions | Architecture decisions теряются при компрессии | Explicit priority list в CLAUDE.md |
| Model switch mid-session | Cache rebuild = дороже, чем продолжить | Subagent handoff или fresh session |
| Нет verification criteria | "Claude says done" ≠ "actually correct" | Explicit acceptance criteria в prompt/skill |
| Hook output без truncation | Output загрязняет контекст | `\| head -30` для всех hooks |
| Side-effect skills с auto-invoke | Неконтролируемые side effects | `disable-model-invocation: true` |

---

## 15. Configuration Health Check

На основе шестислойного framework из этого урока существует open-source skill project для оценки конфигурации:

```bash
npx skills add tw93/claude-health -a claude-code -s health -g -y
```

После установки `/health` в любой сессии. Оценивает:
- Project complexity
- CLAUDE.md quality
- Rules coverage
- Skills design
- Hooks configuration
- AllowedTools settings
- Recurring behavior patterns

Output: приоритизированный отчёт — **fix now**, **structural issues**, **gradual improvements**.

---

## 16. Три стадии использования Claude Code

### Stage 1: Chatbot stage
Спрашиваю → получаю ответ → копирую-вставляю.

### Stage 2: Tool stage
Настраиваю CLAUDE.md, добавляю tools, использую hooks. Claude Code делает больше сам.

### Stage 3: Engineering stage
Вопрос меняется с "как использовать эту фичу?" на **"как заставить агента работать автономно в рамках ограничений?"** Это фундаментально другой concern.

### Практический тест

> Если вы не можете чётко артикулировать, как выглядит "done" — задача, вероятно, не готова для автономного выполнения Claude.

Без acceptance criteria нет reliable notion of a correct answer, независимо от capability модели.

---

## Резюме

**Ключевые инженерные принципы:**

1. **Systems design, не prompt engineering** — проблемы Claude Code решаются на уровне архитектуры, а не формулировок промптов

2. **Шесть слоёв** — CLAUDE.md, Rules, Skills, Tools/MCP, Hooks, Subagents. Каждый слой имеет своё назначение. Over-index на одном → нестабильность

3. **Context = noise problem** — проблема не в capacity, а в signal-to-noise ratio. Layered context loading, Compact Instructions, HANDOFF.md

4. **Hooks + Skills + CLAUDE.md = трёхслойный enforcement** — один слой имеет gaps, три вместе работают

5. **Verification loop обязателен** — "Claude says done" не имеет инженерной ценности без explicit acceptance criteria

6. **Prompt caching как архитектурное ограничение** — порядок контента, стабильность tools, модель-специфичность кеша влияют на стоимость и latency

7. **Progressive disclosure** — не показывайте модели всё сразу. Index → navigation → details on demand

8. **Environment transparency** — converge state first, then expose edit entry points. Doctor commands перед работой
