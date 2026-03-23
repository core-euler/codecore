---
module: "04_skills"
lesson: 4
title: "Примеры Skills и кейсы использования"
type: "example"
prerequisites: ["04_skills/lesson_02"]
difficulty: "intermediate"
tags: ["skills", "examples", "pr-review", "registry", "real-world"]
---

# Примеры Skills и кейсы использования

## Главный тезис

Теория Skills оживает в практических примерах. В этом уроке — реальные кейсы: от PR review до маркетплейсов Skills, от ролевых Skills для разных специалистов до паттернов skill chaining. Каждый пример иллюстрирует принципы из предыдущих уроков.

---

## 1. PR Review Skill: полный разбор

### 1.1 Контекст

Code review — одна из самых популярных задач для Skills. Anthropic внутренне использует несколько вариантов review Skills с разным уровнем строгости.

### 1.2 Skill: adversarial-review

```markdown
---
name: adversarial-review
description: Perform adversarial code review on pull requests.
  Spawns a fresh-eyes subagent to critique changes, implements fixes,
  iterates until findings degrade to nitpicks. Use when user asks
  to review a PR, audit code quality, or check for security issues.
version: "2.1"
tags: ["review", "security", "quality", "pr"]
---

# Adversarial Code Review

## Purpose

This skill performs a thorough, adversarial review of a pull request.
It spawns a separate subagent with a "fresh eyes" perspective that
critiques changes without the bias of having written them. The review
iterates: findings are addressed, then re-reviewed, until only nitpicks
remain.

## Instructions

1. Fetch PR diff and context using `gh pr diff <number>`
2. Execute static analysis: `scripts/security-scan.sh <pr_number>`
3. Spawn review subagent with findings for adversarial critique

## Non-Negotiable Acceptance Criteria

- [ ] Every changed file has been reviewed
- [ ] No HIGH/CRITICAL security findings remain unaddressed
- [ ] All new public endpoints have corresponding tests
- [ ] No hardcoded credentials, tokens, or secrets detected
- [ ] Review iterates until only LOW/NITPICK findings remain

## Output

Write to `review-report.json`:
{
  "pr": <number>,
  "iteration": <count>,
  "findings": [...],
  "verdict": "APPROVE | REQUEST_CHANGES | COMMENT",
  "summary": "<2-3 sentences>"
}

## Available Resources

- `scripts/security-scan.sh` — runs semgrep + custom rules
- `scripts/test-coverage.sh` — checks if coverage decreased
- `references/security-rules.md` — custom security rules for our codebase
- `references/report-schema.json` — JSON schema for output

## Gotchas

- GitHub CLI rate limits: use `--cache 5m` flag for repeated calls
- Large PRs (>500 changed lines): split review by directory
- Draft PRs may not have all CI results — check PR status first
```

### 1.3 Почему этот Skill эффективен

| Принцип | Реализация |
|---------|-----------|
| **Harness optimization** | 3 конкретных шага, чёткие ограничения |
| **Non-Negotiable** | 5 критериев, без которых review не завершается |
| **Progressive disclosure** | Скрипты в `scripts/`, правила в `references/` |
| **Определённый Output** | JSON с фиксированной схемой |
| **Gotchas** | 3 реальных проблемы, обнаруженных в использовании |

### 1.4 Паттерн: итеративный review

Ключевая идея adversarial-review — **итерация**: агент не просто находит проблемы, а цикл «найти → исправить → перепроверить» продолжается до тех пор, пока серьёзных замечаний не остаётся. Это реализация agent loop внутри Skill.

---

## 2. Verification Skills: signup-flow-driver

### 2.1 Контекст

Verification Skills — одна из самых ценных категорий. Anthropic рекомендует **выделить инженера на неделю**, чтобы довести verification Skill до совершенства.

### 2.2 Полный пример

```markdown
---
name: signup-flow-driver
description: Run through the complete signup flow (signup → email verify →
  onboarding) in a headless browser with assertions at each step. Use when
  testing registration, onboarding, or user creation flows.
version: "1.3"
tags: ["verification", "signup", "e2e", "playwright"]
---

# Signup Flow Driver

## Purpose

End-to-end verification of the signup flow using Playwright.
Records a video of the entire flow for visual review and runs
programmatic assertions at each step.

## Instructions

1. Start headless browser with video recording: `scripts/start-browser.sh`
2. Execute signup flow: fill form → submit → check email → verify → onboard
3. Assert state at each step using `scripts/assert-state.py <step>`

## Non-Negotiable Acceptance Criteria

- [ ] Video recording is saved to `outputs/flow-recording.mp4`
- [ ] All 5 assertions pass: form_submitted, email_sent, email_verified,
      onboard_started, onboard_completed
- [ ] No console errors during the flow
- [ ] Flow completes in < 30 seconds

## Output

- Video: `outputs/flow-recording.mp4`
- Report: `outputs/flow-report.json` with timing and assertion results

## Available Resources

- `scripts/start-browser.sh` — launches Playwright with recording
- `scripts/assert-state.py` — checks DB state at each step
- `scripts/cleanup-test-user.sh` — removes test user after run
- `config.json` — test user credentials and URLs

## Gotchas

- Email verification requires mailhog running locally: `docker start mailhog`
- Playwright needs to be installed: `npx playwright install chromium`
- On CI, use `--headed=false` flag explicitly
```

### 2.3 Техники верификации

Из опыта Anthropic, наиболее эффективные verification Skills включают:

1. **Запись видео** — агент может записать видео своего выхода, и вы увидите, что именно он тестировал
2. **Программные assertions** — проверка состояния на каждом шаге (не визуальная, а программная)
3. **Включение скриптов** — готовые скрипты для browser automation, DB state checks, cleanup
4. **Детерминизм** — каждый запуск даёт одинаковый результат

---

## 3. Data Fetching & Analysis Skill

### 3.1 Skill: funnel-query

```markdown
---
name: funnel-query
description: Query and analyze conversion funnels from signup to paid.
  Includes canonical table joins, user_id resolution, and segment definitions.
  Use when analyzing funnels, conversion, or user journey data.
version: "1.0"
tags: ["data", "funnel", "analytics", "conversion"]
---

# Funnel Query

## Purpose

Query conversion funnel data with correct table joins and canonical
user IDs. Eliminates the common mistake of using the wrong user_id
or incorrect event-to-step mapping.

## Instructions

1. Identify the funnel steps from user's request
2. Use helpers from `scripts/data_helpers.py` to build queries
3. Execute and visualize results

## Available Resources

- `scripts/data_helpers.py` — helper functions:
  - `fetch_events(start, end, type)` — events from analytics
  - `resolve_user_id(raw_id)` — maps to canonical user_id
  - `funnel_steps()` — returns canonical step definitions
- `references/tables.md` — schema documentation
- `references/segments.md` — segment definitions

## Gotchas

- The `user_id` in events table is NOT canonical — always join with
  `users.canonical_id`
- Event `signup_completed` fires BEFORE email verification
- Use `event_time` not `created_at` for funnel ordering
- Weekend data has ~30% lower volume — normalize before comparing
```

### 3.2 Паттерн: библиотека хелперов

Ключевой паттерн для data Skills — **готовые хелперы**. Агент не пишет SQL-запросы с нуля, а компонует готовые функции:

```python
# Агент генерирует на лету:
from data_helpers import fetch_events, resolve_user_id, funnel_steps

events = fetch_events("2026-03-14", "2026-03-21", "signup")
canonical_events = [
    {**e, "user_id": resolve_user_id(e["user_id"])}
    for e in events
]
```

Это позволяет агенту тратить шаги на **анализ и композицию**, а не на boilerplate подключения к базе данных.

---

## 4. Business Automation: standup-post

### 4.1 Skill с памятью

```markdown
---
name: standup-post
description: Generate and post daily standup by aggregating ticket tracker,
  GitHub activity, and Slack threads. Shows only deltas from last standup.
  Use when user says "standup", "daily update", or "what did I do yesterday".
version: "2.0"
tags: ["standup", "automation", "slack", "daily"]
---

# Standup Post

## Purpose

Aggregate development activity and post a formatted standup to Slack.
Uses history of previous standups to show only what changed.

## Instructions

1. Load previous standups from `${CLAUDE_PLUGIN_DATA}/standups.log`
2. Fetch: GitHub commits/PRs, ticket tracker updates, Slack mentions
3. Compare with last standup, generate delta-only update

## Non-Negotiable Acceptance Criteria

- [ ] Only changes since last standup are included
- [ ] Posted to correct Slack channel (from config.json)
- [ ] Standup logged to `${CLAUDE_PLUGIN_DATA}/standups.log`

## Output

Slack message format:
**Standup — <date>**
✅ Done: <completed items>
🔄 In Progress: <active items>
🚫 Blocked: <blockers>

## Setup

If `config.json` missing, ask:
1. Slack channel for standup?
2. GitHub username?
3. Ticket tracker project ID?
```

### 4.2 Почему используется `${CLAUDE_PLUGIN_DATA}`

Данные в директории Skill удаляются при обновлении. Лог стендапов — долговременные данные, поэтому они хранятся в `${CLAUDE_PLUGIN_DATA}`, стабильной директории плагина.

---

## 5. Scaffolding Skill: new-migration

### 5.1 Пример

```markdown
---
name: new-migration
description: Create a new database migration file with correct naming,
  template, and common safeguards. Use when user needs to create a
  migration, alter tables, or add columns.
version: "1.0"
tags: ["migration", "database", "scaffold"]
---

# New Migration

## Purpose

Scaffold a database migration with correct naming convention, template,
and built-in safeguards against common mistakes.

## Instructions

1. Generate migration file from `templates/migration.py`
2. Fill in migration logic based on user's request
3. Run `scripts/validate-migration.sh` to check for issues

## Non-Negotiable Acceptance Criteria

- [ ] File name follows pattern: YYYYMMDD_HHMMSS_<description>.py
- [ ] Both up() and down() methods are implemented
- [ ] No DROP TABLE without explicit user confirmation
- [ ] Large table alterations use batched approach

## Available Resources

- `templates/migration.py` — base template with up/down
- `scripts/validate-migration.sh` — checks for common issues
- `references/migration-gotchas.md` — past migration failures

## Gotchas

- Adding NOT NULL column to existing table requires DEFAULT value
- Index creation on large tables: use CONCURRENTLY
- Foreign keys: check that referenced table exists in migration order
```

---

## 6. CI/CD Skill: babysit-pr

### 6.1 Skill для автоматизации PR-lifecycle

```markdown
---
name: babysit-pr
description: Monitor a PR through CI, retry flaky tests, resolve merge
  conflicts, and enable auto-merge when ready. Use when user says
  "watch this PR", "babysit PR", or "help merge PR".
version: "1.5"
tags: ["ci", "pr", "merge", "automation"]
---

# Babysit PR

## Purpose

Automate the tedious parts of getting a PR merged: monitor CI,
retry flaky tests, resolve merge conflicts, enable auto-merge.

## Instructions

1. Watch PR status: `gh pr checks <number> --watch`
2. On flaky test failure, re-trigger: `gh pr checks <number> --rerun`
3. On merge conflict, fetch latest main and resolve

## Non-Negotiable Acceptance Criteria

- [ ] PR passes all required checks
- [ ] No unresolved merge conflicts
- [ ] Auto-merge enabled only after all checks pass
- [ ] Each retry/action logged to `outputs/pr-log.md`

## Gotchas

- Max 3 retries for flaky tests, then escalate to user
- Some CI jobs are not retryable (security scan) — check job name
- Auto-merge requires branch protection rules to be configured
```

### 6.2 Паттерн: мониторинг и эскалация

Babysit-PR демонстрирует важный паттерн: агент **мониторит** процесс и **эскалирует** при необходимости. Не пытается решить всё сам, но автоматизирует рутину.

---

## 7. Runbook Skill: oncall-runner

### 7.1 Skill для on-call расследований

```markdown
---
name: oncall-runner
description: Investigate alerts by checking common suspects, pulling
  relevant logs, and producing a structured finding report. Use when
  an alert fires, an incident starts, or debugging production issues.
version: "1.0"
tags: ["oncall", "debugging", "incident", "runbook"]
---

# On-Call Runner

## Purpose

Given an alert or error, walk through a structured investigation:
check common suspects, pull logs, correlate events, produce a report.

## Instructions

1. Parse the alert/error to identify affected service
2. Run `scripts/check-suspects.sh <service>` for common checks
3. Pull relevant logs: `scripts/fetch-logs.sh <service> <timerange>`

## Non-Negotiable Acceptance Criteria

- [ ] All common suspects checked (see references/suspect-list.md)
- [ ] Logs from at least the last 30 minutes reviewed
- [ ] Related alerts in the same timeframe identified
- [ ] Structured finding report generated

## Output

Finding report in `outputs/finding.md`:
- **Alert**: <original alert>
- **Service**: <affected service>
- **Root Cause**: <identified or "needs escalation">
- **Evidence**: <logs, metrics, correlations>
- **Action**: <recommended next steps>

## Available Resources

- `scripts/check-suspects.sh` — checks health, recent deploys, config changes
- `scripts/fetch-logs.sh` — pulls logs with auto-filtering
- `references/suspect-list.md` — common failure modes per service
- `references/escalation-matrix.md` — who to page for what
```

---

## 8. Skill Registries и маркетплейсы

### 8.1 Два способа распространения Skills

**Способ 1: коммит в репозиторий**

Поместите Skills в `./.claude/skills/` внутри репозитория. Все, кто клонирует репо, автоматически получают Skills.

```
my-project/
├── .claude/
│   └── skills/
│       ├── pr-review/
│       │   └── SKILL.md
│       ├── deploy-service/
│       │   ├── SKILL.md
│       │   └── scripts/
│       └── new-migration/
│           ├── SKILL.md
│           └── templates/
├── src/
└── ...
```

**Подходит для**: небольших команд, немногих репозиториев.

**Ограничение**: каждый закоммиченный Skill немного увеличивает контекст модели.

**Способ 2: Plugin Marketplace**

Создайте внутренний маркетплейс плагинов. Пользователи устанавливают только нужные Skills.

```
/plugin marketplace add <your-org>/skills-marketplace
/plugin install pr-review@your-marketplace
```

**Подходит для**: больших команд, масштабирования.

**Преимущество**: пользователь сам решает, какие Skills установить; ненужные не увеличивают контекст.

### 8.2 Процесс курирования маркетплейса

Опыт Anthropic по управлению внутренним маркетплейсом:

1. **Нет централизованной команды** — полезные Skills находятся органически
2. **Sandbox-папка** — автор загружает новый Skill в sandbox на GitHub и делится ссылкой в Slack
3. **Трекшн** — когда Skill набирает популярность (решает автор), создаётся PR для переноса в маркетплейс
4. **Курирование** — перед добавлением в маркетплейс проверяется качество (легко создать плохие или дублирующие Skills)

### 8.3 Пример: Agent Skills for Context Engineering Marketplace

Открытый маркетплейс от Muratcan Koylan — пример организации Skills в plugin-бандлы:

| Plugin | Включённые Skills |
|--------|-------------------|
| `context-engineering-fundamentals` | context-fundamentals, context-degradation, context-compression, context-optimization |
| `agent-architecture` | multi-agent-patterns, memory-systems, tool-design, filesystem-context, hosted-agents |
| `agent-evaluation` | evaluation, advanced-evaluation |
| `agent-development` | project-development |

Этот маркетплейс цитируется в академических исследованиях (Peking University, 2026) как пример foundational work по static skill architecture.

---

## 9. Skills для разных ролей

### 9.1 QA Engineer

| Skill | Назначение |
|-------|-----------|
| `signup-flow-driver` | E2E тестирование signup |
| `checkout-verifier` | Тестирование оплаты с Stripe test cards |
| `tmux-cli-driver` | Интерактивное CLI-тестирование |
| `testing-practices` | Инструкции по написанию тестов |

### 9.2 Software Architect

| Skill | Назначение |
|-------|-----------|
| `adversarial-review` | Глубокий code review |
| `multi-agent-patterns` | Проектирование агентных систем |
| `context-optimization` | Оптимизация контекста |
| `tool-design` | Проектирование инструментов |

### 9.3 DevOps / SRE

| Skill | Назначение |
|-------|-----------|
| `babysit-pr` | Автоматизация CI/CD |
| `deploy-service` | Безопасный деплой |
| `oncall-runner` | Расследование инцидентов |
| `resource-orphans` | Очистка инфраструктуры |
| `cost-investigation` | Анализ расходов |

### 9.4 Data Analyst

| Skill | Назначение |
|-------|-----------|
| `funnel-query` | Анализ воронок |
| `cohort-compare` | Сравнение когорт |
| `grafana` | Работа с дашбордами |
| `weekly-recap` | Еженедельные отчёты |

### 9.5 Tech Lead

| Skill | Назначение |
|-------|-----------|
| `standup-post` | Автоматический стендап |
| `create-ticket` | Создание тикетов по шаблону |
| `dependency-management` | Управление зависимостями |
| `code-style` | Стандарты кода команды |

---

## 10. Skill Chaining: цепочки Skills

### 10.1 Концепция

Skill chaining — это паттерн, когда выход одного Skill становится входом для другого. Для этого критически важен **определённый формат Output**.

### 10.2 Пример цепочки: от тикета до PR

```
create-ticket
    ↓ (ticket ID)
new-migration
    ↓ (migration file)
testing-practices
    ↓ (test files)
adversarial-review
    ↓ (review report)
babysit-pr
    ↓ (merged PR)
deploy-service
```

Каждый Skill производит артефакт, который использует следующий Skill в цепочке.

### 10.3 Управление зависимостями

Управление зависимостями между Skills пока не встроено в платформу, но можно:

- Ссылаться на другие Skills **по имени** — модель вызовет их, если установлены
- Описывать зависимости в SKILL.md
- Проверять наличие зависимостей в acceptance criteria

```markdown
## Dependencies

This skill requires the following skills to be installed:
- `csv-generator` — for creating output CSV
- `file-uploader` — for uploading results

If a required skill is not available, ask the user to install it.
```

### 10.4 Ограничения chaining

- Если формат выхода одного Skill изменится — цепочка сломается
- Длинные цепочки накапливают ошибки
- Нет формального механизма проверки совместимости версий

---

## 11. On-Demand Hooks: продвинутые паттерны

### 11.1 /careful — защита от деструктивных операций

```markdown
---
name: careful-mode
description: Block dangerous operations like rm -rf, DROP TABLE, force-push,
  kubectl delete. Use when working with production data or critical systems.
hooks:
  - type: PreToolUse
    matcher: Bash
    script: scripts/block-dangerous.sh
---

# Careful Mode

## Purpose

Prevent accidental destructive operations when working near
production. Blocks specific commands via PreToolUse hook.

## Blocked Operations

- `rm -rf` on non-temp directories
- `DROP TABLE`, `TRUNCATE`
- `git push --force` to protected branches
- `kubectl delete` without dry-run
```

Этот Skill активирует hook только когда вызван — держать его включённым постоянно было бы невыносимо, но при работе с production он критически важен.

### 11.2 /freeze — ограничение области изменений

```markdown
---
name: freeze-scope
description: Block all file edits outside a specific directory. Use when
  debugging to add logs without accidentally changing unrelated code.
hooks:
  - type: PreToolUse
    matcher: Edit,Write
    script: scripts/check-scope.sh
---

# Freeze Scope

## Setup

Ask user: "Which directory should be writable?"
Store in config.json.

## Purpose

During debugging, prevents accidental changes outside the target
directory. Useful when you want to add logging but keep everything
else frozen.
```

---

## 12. Измерение и аналитика Skills

### 12.1 PreToolUse hook для логирования

Anthropic использует `PreToolUse` hook для логирования использования Skills:

```javascript
// Пример: логирование skill usage
{
  "type": "PreToolUse",
  "handler": async (event) => {
    if (event.skill_activated) {
      log({
        skill: event.skill_name,
        user: event.user_id,
        timestamp: Date.now(),
        trigger: event.trigger_query
      });
    }
  }
}
```

### 12.2 Метрики

| Метрика | Назначение |
|---------|-----------|
| **Trigger rate** | Как часто Skill срабатывает |
| **Success rate** | Доля завершений с выполненными acceptance criteria |
| **Undertrigger** | Skill срабатывает реже ожидаемого — нужно уточнить description |
| **Overtrigger** | Skill срабатывает когда не нужен — description слишком широкий |
| **Usage by team** | Какие команды используют какие Skills |

### 12.3 Lifecycle Skills

Здоровый lifecycle Skill:

1. **Создание** — минимальная версия, несколько строк + один gotcha
2. **Adoption** — коллеги начинают использовать, появляются первые отзывы
3. **Итерация** — добавляются gotchas, скрипты, reference-файлы
4. **Стабилизация** — Skill покрывает основные сценарии, acceptance criteria отточены
5. **Распространение** — перенос в маркетплейс для более широкой аудитории

---

## 13. Real-World паттерны использования

### 13.1 Паттерн: Skill + MCP Tool

Skill содержит знания *как*, MCP Tool даёт возможность *выполнить*:

```
Skill: deploy-service
  Знает: порядок деплоя, smoke tests, rollback criteria
  +
MCP Tool: kubernetes-api
  Умеет: применять manifests, проверять pod status, откатывать
  =
Результат: безопасный, знающий деплой
```

### 13.2 Паттерн: Skill для onboarding

Новый инженер устанавливает набор Skills и получает экспертизу команды:

```
/plugin install billing-lib@internal      # знания о биллинге
/plugin install internal-cli@internal     # все команды CLI
/plugin install deploy-staging@internal   # как деплоить на staging
/plugin install testing-practices@internal # как писать тесты
```

Вместо чтения 50 страниц документации, новичок получает **контекстные** подсказки в момент, когда они нужны.

### 13.3 Паттерн: Skill для code style

Skill, который корректирует стиль кода в областях, где Claude по умолчанию ошибается:

```markdown
## Code Style — Our Standards

### Non-obvious rules
- Prefer `Result<T, E>` over exceptions in service boundaries
- Use newtype pattern for all IDs (no raw strings/numbers)
- Error messages must include request_id for tracing
- All database queries must use named parameters (not positional)

### Claude's common mistakes with our codebase
- Defaults to `try/catch` — we use Result types
- Generates `console.log` — we use structured logger
- Uses inline SQL — we require query builder
```

Ценность этого Skill — именно в **нестандартных** требованиях, которые Claude не может вывести из общих знаний.

---

## Итоги

1. **adversarial-review** — паттерн итеративного review с fresh-eyes subagent
2. **Verification Skills** — самые ценные; стоят инвестиций инженерного времени
3. **Data Skills** — готовые хелперы позволяют агенту компоновать вместо написания boilerplate
4. **Маркетплейсы** — два пути распространения: коммит в репо или plugin marketplace
5. **Skill chaining** — цепочки работают только при строго определённом Output
6. **On-demand hooks** — /careful и /freeze для ситуативной безопасности
7. **Измерение** — PreToolUse hooks для логирования и аналитики usage
8. **Ролевые наборы** — разные специалисты используют разные комбинации Skills
9. **Onboarding** — Skills как способ передачи экспертизы команды новичкам
