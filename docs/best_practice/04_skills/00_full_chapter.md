---
module: "04_skills"
lesson: 0
title: "Agent Skills — полная глава"
type: "reference"
prerequisites: ["03_context_engineering"]
difficulty: "intermediate"
tags: ["skills", "harness", "creation", "context-engineering", "examples"]
---

# Agent Skills — полная глава

Модуль покрывает четыре темы: что такое Agent Skills и зачем они нужны, как создавать Skills по принципам harness optimization, как Skills реализуют context engineering, и реальные примеры Skills для разных ролей. Вместе они дают полную картину — от концепции до production-ready Skills.

---

## 1. Что такое Agent Skills

### 1.1 Определение

Agent Skill — это **модульный, переиспользуемый набор файлов**, который превращает универсального LLM-агента в специализированного эксперта. Skill — не промпт, а папка с инструкциями, скриптами, данными и ассетами, которую агент автоматически обнаруживает и загружает по требованию.

### 1.2 Ключевые характеристики

| Характеристика | Описание |
|----------------|----------|
| **Модульность** | Каждый Skill инкапсулирует знания по одной дисциплине |
| **Переиспользуемость** | Один Skill работает во многих сессиях и контекстах |
| **Загрузка по требованию** | Содержимое загружается только при необходимости |
| **Файловая система** | Skills существуют как директории с структурированным содержимым |
| **Автоматическое обнаружение** | Агент сам определяет, когда нужен конкретный Skill |

### 1.3 Skills vs промпты

| Аспект | Промпты | Skills |
|--------|---------|--------|
| Область применения | Одна сессия | Многие сессии |
| Переиспользуемость | Ручная репликация | Автоматическое обнаружение |
| Контекстная стоимость | Всегда в контексте | Загружается при необходимости |
| Управление версиями | Теряется в сессии | Версионируется на файловой системе |
| Состав | Только текст | Текст + скрипты + данные + шаблоны |

---

## 2. Архитектура Skills

### 2.1 Файловая структура

Минимум — один файл `SKILL.md`. Полная структура:

```
my-skill/
  SKILL.md              # Основные инструкции (обязателен)
  examples/             # Готовые примеры кода
  scripts/              # Исполняемые скрипты
  templates/            # Шаблоны для генерации
  references/           # Детальная документация, API
  assets/               # Вспомогательные данные
```

### 2.2 YAML Frontmatter

```yaml
---
name: pdf-processing          # kebab-case, 15-40 символов (обязательно)
description: Extract text and tables from PDF files, fill forms.
  Use when working with PDF files or document extraction.  # (обязательно)
version: "1.0"
author: "Claude Skills Team"
tags: ["pdf", "extraction"]
---
```

**Поле description** — для модели, не для человека. По нему агент решает, нужен ли Skill для текущего запроса. Структура: `<Что делает>. <Когда использовать>.`

### 2.3 Progressive Disclosure: трёхуровневая загрузка

| Уровень | Когда | Стоимость | Содержимое |
|---------|-------|-----------|------------|
| 1. Metadata | Всегда | ~100 токенов | `name`, `description` из YAML |
| 2. Instructions | При триггере | ~3-5K токенов | SKILL.md body |
| 3. Resources | По требованию | Через bash | Скрипты, шаблоны, данные |

Можно иметь десятки и сотни Skills без загромождения контекстного окна. Агент загрузит только нужные.

**Алгоритм обнаружения:** при старте сессии индексируются метаданные -> при запросе пользователя semantic search по описаниям -> при превышении порога загружаются инструкции.

---

## 3. Типы Skills: таксономия

9 категорий по классификации Anthropic:

| Категория | Примеры | Особенности |
|-----------|---------|-------------|
| **Library & API Reference** | `billing-lib`, `internal-cli` | Справочники по библиотекам с gotchas |
| **Product Verification** | `signup-flow-driver`, `checkout-verifier` | Самые ценные; стоят недели инженерного времени |
| **Data Fetching & Analysis** | `funnel-query`, `cohort-compare` | Библиотеки хелперов для получения данных |
| **Business Automation** | `standup-post`, `create-ticket` | Автоматизация повторяющихся процессов |
| **Code Scaffolding** | `new-migration`, `create-app` | Генерация boilerplate |
| **Code Quality & Review** | `adversarial-review`, `code-style` | Code review, автоматический через hooks |
| **CI/CD & Deployment** | `babysit-pr`, `deploy-service` | Автоматизация CI/CD |
| **Runbooks** | `oncall-runner`, `log-correlator` | Расследование инцидентов |
| **Infrastructure** | `resource-orphans`, `cost-investigation` | Обслуживание инфраструктуры |

Лучшие Skills чётко попадают в одну категорию; размытые между несколькими вызывают путаницу.

---

## 4. Когда использовать Skills vs другие подходы

| Ситуация | Рекомендация |
|----------|-------------|
| Инструкции нужны в каждой сессии и коротки | System Prompt |
| Нужно вызвать внешний API | MCP Tool |
| Нужна экспертиза по предметной области | Skill |
| Нужно параллельно решить несколько задач | Subagent |
| Инструкции объёмные и переиспользуются | Skill |
| Нужно выполнить действие + знать как | Skill + MCP Tool |

Skills и MCP часто работают вместе: Skill содержит знания **как**, MCP даёт возможность **выполнить**.

---

## 5. Создание Skills: harness optimization

### 5.1 Что такое harness

Harness — набор ограничений и структур, внутри которых работает агент. Чем точнее рамки — тем лучше результат. Это не промптинг, а **дизайн систем**.

Принцип: больше ограничений -> лучше результат. Агент не тратит ресурсы на решения, которые вы уже приняли, снижается вероятность ошибок, результат воспроизводим.

> Если Skill требует более 3 шагов — разделите его на несколько Skills.

### 5.2 Пять обязательных секций

**1. Metadata** — name, description, триггеры.

**2. Purpose** — один параграф, суть Skill. Агент должен понять идею с первого прочтения.

**3. Instructions** — пошаговые инструкции. Каждый шаг чёткий и конкретный. Точные пути к скриптам.

**4. Non-Negotiable Acceptance Criteria** — самая важная секция. Агент не завершает работу, пока все критерии не выполнены.

| Формулировка | Поведение агента |
|-------------|------------------|
| Rules | Воспринимает как рекомендации |
| Objectives | Стремится, но может «срезать углы» |
| **Non-Negotiable** | Абсолютное требование, не завершает без выполнения |

**5. Output** — точный формат выхода (JSON schema, markdown шаблон). Без него цепочки Skills не работают.

### 5.3 Best Practices от Anthropic

**Не пишите очевидное.** Claude хорошо разбирается в программировании. Фокусируйтесь на информации, которая выводит агента за рамки привычного мышления.

**Соберите раздел Gotchas.** Самый ценный контент в любом Skill. Начните с пустого и обновляйте при каждой ошибке агента:

```markdown
## Gotchas
- `pdfplumber` не поддерживает зашифрованные PDF — используй `pikepdf`
- Таблицы без границ не определяются `extract_tables()` — используй `extract_words()`
```

**Используйте файловую систему.** Вынесите API-референсы в `references/`, длинные примеры в `examples/`, шаблоны в `templates/`. SKILL.md работает как индекс, ссылаясь на детали.

**Не загоняйте в жёсткие рамки.** Описывайте *что* сделать и *какие критерии* выполнить, но оставляйте свободу в *как*.

**Продумайте начальную настройку.** Если Skill нужен контекст от пользователя — храните его в `config.json` внутри Skill.

**Храните скрипты.** Готовый код позволяет агенту тратить шаги на композицию, а не на boilerplate.

### 5.4 Типичные ошибки

| Ошибка | Симптом | Решение |
|--------|---------|---------|
| Делает слишком много | 7+ шагов, агент путается | Разделите на 2-3 Skill |
| Нет acceptance criteria | Завершается в произвольный момент | Добавьте Non-Negotiable |
| Слишком общее описание | Срабатывает/не срабатывает не вовремя | Конкретные триггеры в description |
| Нет формата выхода | Разный формат каждый раз | JSON schema или шаблон в Output |
| Инструкции слишком жёсткие | Работает для одного сценария | Опишите цель, не метод |
| Нет Gotchas | Одни и те же грабли | Обновляйте после каждого сбоя |

### 5.5 Итеративное улучшение

1. Начните с минимума — Purpose + 3 шага + Acceptance Criteria + Output
2. Запустите на реальных задачах
3. Наблюдайте, где агент ошибается
4. Дополняйте gotchas, скрипты, reference-файлы
5. Повторяйте — каждая итерация делает Skill надёжнее

Для измерения: `PreToolUse` hook для логирования trigger rate, success rate, undertrigger/overtrigger.

---

## 6. Skills и Context Engineering

### 6.1 Как Skills реализуют CE

| Принцип CE | Реализация в Skills |
|-----------|---------------------|
| Минимизация контекста | Метаданные — ~100 токенов на Skill |
| Загрузка по необходимости | Инструкции при триггере |
| Offloading | Ресурсы через bash, не в основном контексте |
| Релевантность | Semantic search по описаниям |

**Filesystem как контекст:** агент знает, *где* найти информацию, и загружает по необходимости. Это паттерн tool output offloading.

**SKILL.md как индекс:** содержит обзор (десятки токенов) со ссылками на полный код и документацию.

### 6.2 Каталог CE-специализированных Skills

**Foundational:** context-fundamentals, context-degradation (lost-in-middle, context poisoning), context-compression.

**Architectural:** multi-agent-patterns, memory-systems, tool-design, filesystem-context, hosted-agents.

**Operational:** context-optimization (compaction, masking, caching), evaluation, advanced-evaluation.

**Development Methodology:** project-development (полный цикл LLM-проекта).

**Cognitive Architecture:** bdi-mental-states (BDI-онтология для агентов).

### 6.3 Паттерны context-aware Skills

**Context Budget Manager** — отслеживает расход контекстного бюджета, применяет компрессию при > 70% capacity. Критическая информация никогда не удаляется.

**Dynamic Context Discovery** — скрипт `find-related.py` обнаруживает связанные файлы, загружает только релевантные. Карта навигации сохраняется для повторного использования.

**Scratch Pad / Plan Persistence** — план задачи записывается в файл, каждый шаг отмечается как выполненный. При потере контекста агент перечитывает план.

**Context Compression** — сжатие истории длительных сессий: группировка tool calls, замена verbose outputs саммари, извлечение ключевых решений.

**Memory-Augmented Skill** — append-only JSONL-файлы для долговременной памяти между сессиями.

### 6.4 Принципы проектирования

- **SKILL.md < 500 строк** — всё длиннее выносится в reference-файлы
- **Platform Agnosticism** — паттерны работают в Claude Code, Cursor и любой другой агентной платформе
- **Критическая информация — в начале и в конце** (U-shaped attention)
- **Non-Negotiable Acceptance Criteria — ближе к концу** (last-token advantage)

### 6.5 Антипаттерны

- Загрузка всей документации в SKILL.md вместо ссылок на `references/`
- Хранение промежуточных результатов в контексте вместо `scratch/`
- Важная информация в середине длинного SKILL.md
- Монолитные Skills на 1000+ строк вместо декомпозиции

### 6.6 Многоуровневая архитектура

```
Уровень 3: Task-specific Skills
  (pr-review, data-analysis, deploy-service)
        | используют
Уровень 2: Architectural Skills
  (memory-systems, multi-agent-patterns, tool-design)
        | опираются на
Уровень 1: Foundational Skills
  (context-fundamentals, context-degradation, context-compression)
```

---

## 7. Примеры Skills

### 7.1 adversarial-review (Code Quality)

Итеративный code review с fresh-eyes subagent. 3 шага инструкций, 5 non-negotiable criteria (каждый файл проверен, нет HIGH-находок, тесты для новых endpoints, нет секретов). Output — JSON с findings, verdict и summary. Цикл «найти -> исправить -> перепроверить» до тех пор, пока серьёзных замечаний не останется.

### 7.2 signup-flow-driver (Verification)

E2E верификация signup flow через Playwright с записью видео и программными assertions на каждом шаге. Criteria: видео сохранено, 5 assertions пройдены, нет console errors, flow < 30 секунд.

### 7.3 funnel-query (Data Analysis)

Анализ конверсионных воронок с готовыми хелперами (`fetch_events`, `resolve_user_id`, `funnel_steps`). Агент компонует функции вместо написания SQL с нуля. Gotchas: user_id в events НЕ каноничный, event_time вместо created_at.

### 7.4 standup-post (Business Automation)

Skill с памятью: агрегирует GitHub, трекер, Slack, показывает только дельту от прошлого стендапа. Данные хранятся в `${CLAUDE_PLUGIN_DATA}/standups.log` (стабильная директория, не удаляется при обновлении Skill).

### 7.5 babysit-pr (CI/CD)

Мониторит PR через CI, retry flaky tests (макс. 3), резолвит merge conflicts, включает auto-merge. Паттерн мониторинга и эскалации — автоматизирует рутину, эскалирует при необходимости.

### 7.6 oncall-runner (Runbook)

Расследование алертов: parse alert -> check suspects -> pull logs -> корреляция -> structured finding report (alert, service, root cause, evidence, action).

### 7.7 On-Demand Hooks

- `/careful` — блокирует `rm -rf`, `DROP TABLE`, `force-push`, `kubectl delete` через PreToolUse. Активируется только при работе с production
- `/freeze` — блокирует Edit/Write вне указанной директории. Для отладки без случайных изменений

---

## 8. Распространение и маркетплейсы

### 8.1 Два способа

**Коммит в репозиторий** — `.claude/skills/` внутри проекта. Все, кто клонирует, получают Skills. Подходит для небольших команд.

**Plugin Marketplace** — внутренний маркетплейс, пользователи устанавливают нужное:

```
/plugin marketplace add <org>/skills-marketplace
/plugin install pr-review@marketplace
```

### 8.2 Процесс курирования (опыт Anthropic)

1. Нет централизованной команды — полезные Skills находятся органически
2. Автор загружает в sandbox на GitHub, делится в Slack
3. При набирании популярности — PR для переноса в маркетплейс
4. Курирование: проверка качества перед добавлением

### 8.3 Skill Chaining

Выход одного Skill становится входом для другого:

```
create-ticket -> new-migration -> testing-practices -> adversarial-review -> babysit-pr -> deploy-service
```

Работает только при строго определённом Output. Длинные цепочки накапливают ошибки.

---

## 9. Skills для разных ролей

| Роль | Skills |
|------|--------|
| **QA Engineer** | signup-flow-driver, checkout-verifier, tmux-cli-driver, testing-practices |
| **Architect** | adversarial-review, multi-agent-patterns, context-optimization, tool-design |
| **DevOps / SRE** | babysit-pr, deploy-service, oncall-runner, resource-orphans, cost-investigation |
| **Data Analyst** | funnel-query, cohort-compare, grafana, weekly-recap |
| **Tech Lead** | standup-post, create-ticket, dependency-management, code-style |

Skills как **onboarding**: новый инженер устанавливает набор Skills и получает экспертизу команды контекстно, в момент, когда она нужна.

---

## 10. Память и хранение данных

Skills могут хранить данные между сессиями:

- **Append-only текстовый лог** (standups.log)
- **JSON-файлы** (config.json, entities.jsonl)
- **SQLite-база данных**

Для долговременного хранения: `${CLAUDE_PLUGIN_DATA}` — стабильная директория, не удаляется при обновлении Skill.

---

## 11. Сводка ключевых идей модуля

1. **Skills — папки, не файлы.** Инструкции + скрипты + данные + шаблоны
2. **Progressive Disclosure** — 3 уровня загрузки оптимизируют контекст (метаданные ~100 токенов, инструкции ~3-5K, ресурсы через bash)
3. **Harness optimization** — ограничения улучшают качество; посредственный агент в строгом harness превосходит способного в хаосе
4. **5 секций Skill:** Metadata, Purpose, Instructions, Non-Negotiable Acceptance Criteria, Output
5. **Gotchas — самый ценный контент.** Формируется итеративно, по реальным ошибкам
6. **SKILL.md < 500 строк.** Всё остальное — в reference-файлах
7. **Context engineering через Skills:** filesystem offloading, dynamic discovery, scratch pad, compression, memory
8. **Skill chaining** работает только при определённом формате Output
9. **Verification Skills — самые ценные.** Anthropic рекомендует выделить инженера на неделю для их создания

---

## Ссылки и ресурсы

- [Claude Skills Documentation](https://code.claude.com/docs/en/skills)
- [Agent Skills Course (Anthropic)](https://anthropic.skilljar.com/introduction-to-agent-skills)
- [Skills Examples Repository](https://github.com/anthropics/skills)
- [Agent Skills for Context Engineering](https://github.com/muratcankoylan/context-engineering-skills)
- [3 Principles for Designing Agent Skills (Block)](https://engineering.block.xyz/blog/3-principles-for-designing-agent-skills)
