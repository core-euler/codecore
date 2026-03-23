---
module: "04_skills"
lesson: 2
title: "Создание Skills — паттерны и harness optimization"
type: "theory"
prerequisites: ["04_skills/lesson_01"]
difficulty: "intermediate"
tags: ["skills", "harness", "acceptance-criteria", "creation", "patterns"]
---

# Создание Skills — паттерны и harness optimization

## Главный тезис

Создание эффективного Skill — это **системный дизайн**, а не промпт-инжиниринг. Ключевой принцип — **harness optimization**: ограничение того, что агент *может* делать, чтобы то, что он *делает*, было выполнено качественно. Посредственный агент внутри строгого harness превосходит более способного агента в хаотичной среде.

---

## 1. Harness Optimization: философия создания Skills

### 1.1 Что такое harness

Harness (букв. «упряжь») — это набор ограничений и структур, внутри которых работает агент. Идея проста: чем точнее вы определите рамки, тем лучше агент выполнит задачу.

Это не промптинг. Это **дизайн систем**.

```
Без harness:
  "Сделай code review" → агент делает что-то... непредсказуемо

С harness:
  "Выполни code review по этим 5 критериям,
   используй этот скрипт для проверки,
   результат запиши в этом формате,
   не завершай без прохождения всех acceptance criteria"
  → агент работает предсказуемо и качественно
```

### 1.2 Принцип: больше ограничений → лучше результат

Кажется контринтуитивным: ограничения улучшают качество. Но это работает, потому что:

- Агент не тратит ресурсы на принятие решений, которые вы уже приняли
- Снижается вероятность ошибочных интерпретаций
- Результат становится воспроизводимым
- Можно строить цепочки из предсказуемых Skills

### 1.3 Специализация vs универсальность

Если Skill пытается делать слишком много — разделите его. Правило:

> Если Skill требует более 3 шагов — разделите его на несколько Skills.

Специализированный агент, работающий в узком домене, почти всегда превосходит универсального. Каждый Skill должен быть экспертом в одной вещи.

---

## 2. Анатомия Skill: пять обязательных секций

Формат, который даёт стабильные результаты в 90% случаев, содержит пять секций:

### 2.1 Metadata

```yaml
---
name: pr-review
description: Review pull requests for security, performance, and code quality.
  Use when user asks to review a PR or check code quality.
version: "1.0"
---
```

Имя, описание, триггеры. LLM хорошо распознают эти секции — они не должны быть сложными. Функциональность и точность важнее литературного стиля.

### 2.2 Skill Purpose

Один короткий параграф. Это «pitch» — объяснение основной идеи. Агент должен понять суть с первого прочтения. Детали идут потом.

```markdown
## Purpose

This skill performs adversarial code review on pull requests.
It spawns a fresh-eyes subagent to critique the changes, implements fixes,
and iterates until findings degrade to nitpicks.
```

### 2.3 Instructions

Пошаговые инструкции. Каждый шаг — чёткий и конкретный. Если нужно выполнить скрипт, указывайте точный путь:

```markdown
## Instructions

1. Read the PR diff using `gh pr diff <number>`
2. Execute security scan: `~/scripts/security-check.py --pr <number>`
3. Analyze results and categorize findings by severity
```

**Правило трёх шагов**: если инструкция требует более 3 шагов, это сигнал к декомпозиции на несколько Skills.

### 2.4 Non-Negotiable Acceptance Criteria

**Самая важная секция.** Здесь определяется, что НЕ подлежит обсуждению. Агент не завершает работу, пока все критерии не выполнены.

```markdown
## Non-Negotiable Acceptance Criteria

- [ ] All security findings with severity >= HIGH are addressed
- [ ] No new dependencies without license check
- [ ] Test coverage does not decrease
- [ ] Performance benchmarks pass baseline thresholds
```

#### Почему «Non-Negotiable», а не «Rules»

Многие авторы Skills используют секции «Rules» или «Objectives». Это слабее.

| Формулировка | Поведение агента |
|-------------|------------------|
| **Rules** | Агент воспринимает как рекомендации. Может решить, что в данной ситуации правило не применимо |
| **Objectives** | Агент стремится к цели, но может «срезать углы» |
| **Non-Negotiable** | Агент воспринимает как абсолютное требование. Не завершает работу без выполнения |

Слово «Non-Negotiable» создаёт **обязательство**. Слово «Rules» открывает дверь для интерпретации — агент может решить, что выполнить нужно, а что можно пропустить.

### 2.5 Output

Точное определение формата выхода. Без этого агент будет выдавать разный формат каждый раз, и цепочки Skills не будут работать.

```markdown
## Output

Generate a structured review report in the following format:

```json
{
  "pr_number": <number>,
  "findings": [
    {
      "severity": "HIGH|MEDIUM|LOW|NITPICK",
      "category": "security|performance|style|logic",
      "file": "<path>",
      "line": <number>,
      "description": "<finding>",
      "suggestion": "<fix>"
    }
  ],
  "summary": "<1-2 sentence summary>",
  "verdict": "APPROVE|REQUEST_CHANGES|COMMENT"
}
```

Без определённого формата нельзя:
- Надёжно парсить результат
- Передавать output в следующий Skill в цепочке
- Сравнивать результаты разных запусков

---

## 3. Полный пример: Skill для code review

```markdown
---
name: adversarial-review
description: Perform adversarial code review on pull requests. Use when
  user asks to review a PR, check code quality, or audit security.
version: "2.0"
tags: ["review", "security", "quality"]
---

# Adversarial Code Review

## Purpose

Perform a thorough, adversarial review of a pull request by spawning
a fresh-eyes subagent that critiques changes without bias. Iterate
until findings degrade to nitpicks only.

## Instructions

1. Fetch the PR diff and changed files list
2. Run static analysis scripts from `scripts/` directory
3. Evaluate each changed file against the acceptance criteria

## Non-Negotiable Acceptance Criteria

- [ ] Every file in the diff has been reviewed
- [ ] No HIGH severity security findings remain unaddressed
- [ ] All new public API endpoints have corresponding tests
- [ ] No hardcoded credentials or secrets detected

## Output

Write findings to `review-report.json` using the schema in
`references/report-schema.json`. Include a human-readable
summary as the first section.
```

---

## 4. Best Practices от Anthropic

Эти рекомендации основаны на опыте использования сотен Skills внутри Anthropic.

### 4.1 Не пишите очевидное

Claude Code много знает о кодовой базе и хорошо разбирается в программировании. Если ваш Skill в первую очередь про знания — сфокусируйтесь на информации, которая **выводит агента за рамки привычного мышления**.

Пример: Skill `frontend-design` был создан инженером Anthropic итеративно с пользователями, чтобы улучшить «дизайн-вкус» Claude и избежать стандартных паттернов (шрифт Inter, фиолетовые градиенты). Ценность Skill — именно в нестандартных рекомендациях.

**Плохо** (очевидное):
```markdown
## Instructions
- Write clean code
- Follow best practices
- Use meaningful variable names
```

**Хорошо** (специфичное):
```markdown
## Gotchas
- Our billing library throws silently on negative amounts — always validate
- The user_id in events table is NOT the canonical one; join with users.canonical_id
- React components in /shared must not import from /features (circular dep)
```

### 4.2 Соберите раздел Gotchas

**Самый ценный контент** в любом Skill — раздел с типичными ошибками (Gotchas). Он должен формироваться на основе **реальных** проблем, с которыми агент сталкивается при выполнении задач.

Рекомендация: начните с пустого Gotchas и **обновляйте его** каждый раз, когда агент допускает новую ошибку. Со временем этот раздел становится самой ценной частью Skill.

```markdown
## Gotchas

- `pdfplumber` не поддерживает зашифрованные PDF — используй `pikepdf` для дешифрования
- На macOS `brew install poppler` нужен ДО установки `pdf2image`
- Таблицы без границ (borderless) не определяются `extract_tables()` — используй
  `extract_words()` и группируй по координатам
```

### 4.3 Используйте файловую систему и progressive disclosure

Skill — это папка. Воспринимайте файловую систему как инструмент **context engineering**:

- Укажите агенту, какие файлы есть в Skill — он прочитает их в нужный момент
- Вынесите детальные сигнатуры функций в `references/api.md`
- Если результат — markdown-файл, включите шаблон в `assets/`
- Храните готовые скрипты, которые агент может запускать напрямую

```markdown
## Available Resources

- `references/api.md` — full API documentation for all endpoints
- `scripts/validate.py` — run after each change to verify correctness
- `templates/report.md` — output template, copy and fill
- `examples/` — working code examples for common scenarios
```

Простейшая форма progressive disclosure — ссылки на другие markdown-файлы внутри Skill.

### 4.4 Не загоняйте агента в жёсткие рамки

Claude старается следовать инструкциям. Поскольку Skills многократно переиспользуются, **слишком конкретные** указания бывают вредны. Давайте агенту нужную информацию, но оставляйте гибкость.

**Плохо** (railroading):
```markdown
## Instructions
1. Open the file with vim
2. Go to line 42
3. Change "foo" to "bar"
4. Save and exit
```

**Хорошо** (информация + гибкость):
```markdown
## Instructions
1. Find all references to the deprecated `foo` API
2. Replace with the new `bar` API, preserving existing error handling
3. Run the test suite to verify no regressions
```

Первый вариант не оставляет агенту пространства для адаптации. Второй — даёт цель и критерии, но позволяет выбрать метод.

### 4.5 Продумайте начальную настройку

Некоторым Skills нужен контекст от пользователя. Хороший паттерн — хранить настройки в `config.json` внутри директории Skill:

```markdown
## Setup

This skill requires configuration. If `config.json` does not exist
in the skill directory, ask the user:

1. Which Slack channel to post standup to?
2. What timezone to use for "yesterday" calculation?
3. Which GitHub repos to monitor?

Store answers in `config.json`:
```json
{
  "slack_channel": "#team-standup",
  "timezone": "Europe/Moscow",
  "repos": ["org/backend", "org/frontend"]
}
```

If config exists, proceed without asking.
```

Если нужно показать структурированные вопросы с вариантами ответов, можно указать агенту использовать инструмент `AskUserQuestion`.

### 4.6 Храните скрипты и генерируйте код

Один из самых мощных инструментов — **готовый код в директории Skill**. Скрипты и библиотеки позволяют агенту тратить свои шаги на композицию, а не на воссоздание boilerplate.

Пример: data science Skill может содержать библиотеку функций для получения данных:

```python
# scripts/data_helpers.py

def fetch_events(start_date, end_date, event_type=None):
    """Fetch events from the event source."""
    ...

def get_user_cohort(cohort_name):
    """Get user IDs for a named cohort."""
    ...

def compute_retention(user_ids, period_days=7):
    """Compute retention metrics for a set of users."""
    ...
```

Агент может генерировать скрипты на лету, компонуя эти функции для ответа на вопросы вроде «Что произошло во вторник?» — вместо того чтобы каждый раз заново писать код подключения к базе.

---

## 5. Структура SKILL.md: полный шаблон

### 5.1 Рекомендуемая структура

```markdown
---
name: <kebab-case-name>
description: <What it does>. <When to use>.
version: "1.0"
author: "<team or person>"
tags: ["tag1", "tag2"]
---

# <Skill Name>

## Purpose

<1 paragraph: what this skill does and why>

## Instructions

1. <Step 1: specific action>
2. <Step 2: specific action>
3. <Step 3: specific action>

## Non-Negotiable Acceptance Criteria

- [ ] <Criterion 1>
- [ ] <Criterion 2>
- [ ] <Criterion 3>

## Output

<Exact format specification>

## Available Resources

- `scripts/<name>` — <description>
- `references/<name>` — <description>
- `templates/<name>` — <description>

## Gotchas

- <Known issue 1>
- <Known issue 2>

## Setup (if needed)

<Configuration requirements>
```

### 5.2 Что НЕ включать

- **Очевидные инструкции** — «пиши чистый код», «используй осмысленные имена»
- **Длинные API-референсы** — вынесите в `references/`
- **Примеры кода длиннее 20 строк** — вынесите в `examples/`
- **Все edge cases** — начните с основных, дополняйте по мере обнаружения

---

## 6. Типичные ошибки при создании Skills

### 6.1 Skill делает слишком много

**Симптом**: инструкция содержит 7+ шагов, агент путается на середине.

**Решение**: разделите на 2-3 Skill, каждый из которых делает одну вещь хорошо.

### 6.2 Нет acceptance criteria

**Симптом**: агент «завершает» работу в произвольный момент, результат неполный.

**Решение**: добавьте Non-Negotiable Acceptance Criteria. Агент не может завершить без их выполнения.

### 6.3 Слишком общее описание

**Симптом**: Skill срабатывает когда не нужен, или не срабатывает когда нужен.

**Решение**: опишите в `description` конкретные триггеры: «Use when user asks to...», «Use when working with...»

### 6.4 Нет формата выхода

**Симптом**: каждый раз агент выдаёт результат в разном формате, цепочки Skills ломаются.

**Решение**: определите точный формат в секции Output — JSON schema, markdown шаблон, или структурированный текст.

### 6.5 Инструкции слишком жёсткие

**Симптом**: Skill работает идеально для одного сценария и ломается для всех остальных.

**Решение**: опишите *что* нужно сделать и *какие критерии* выполнить, но оставьте агенту свободу в *как*.

### 6.6 Нет Gotchas

**Симптом**: агент наступает на одни и те же грабли снова и снова.

**Решение**: после каждого сбоя добавляйте gotcha. Со временем Skill становится устойчивее.

---

## 7. Skill Creator

Anthropic выпустила инструмент **Skill Creator** для упрощения создания Skills в Claude Code. Он помогает:

- Сформировать структуру Skill по шаблону
- Подобрать правильное описание
- Итеративно тестировать и улучшать Skill

Тем не менее, понимание принципов harness optimization и структуры Skills остаётся критически важным для создания действительно эффективных Skills.

---

## 8. Итеративное улучшение

### 8.1 Цикл улучшения Skill

Большинство Skills в Anthropic начинались с нескольких строк и одного gotcha. Они стали лучше, потому что авторы дополняли их по мере обнаружения новых edge cases.

Рекомендуемый процесс:

1. **Начните с минимума** — Purpose + 3 шага инструкций + Acceptance Criteria + Output
2. **Используйте** — запустите Skill на реальных задачах
3. **Наблюдайте** — где агент ошибается? Что делает не так?
4. **Дополняйте** — добавьте gotcha, уточните инструкцию, добавьте скрипт
5. **Повторите** — каждая итерация делает Skill надёжнее

### 8.2 Измерение эффективности

Anthropic использует `PreToolUse` hook для логирования использования Skills внутри компании. Это позволяет:

- Находить популярные Skills
- Обнаруживать Skills, которые срабатывают реже ожидаемого
- Оценивать качество через анализ результатов

Пример паттерна: если Skill `pr-review` срабатывает на 60% PR-ревью, но не на оставшихся 40% — нужно уточнить описание или триггеры.

---

## Итоги

1. **Harness optimization** — ключевой принцип: ограничения улучшают качество
2. **5 секций** Skill: Metadata, Purpose, Instructions, Non-Negotiable Acceptance Criteria, Output
3. **«Non-Negotiable»** сильнее «Rules» — создаёт обязательство, а не рекомендацию
4. **Правило трёх шагов** — если больше 3, разделяйте на несколько Skills
5. **Gotchas** — самый ценный контент, формируется итеративно
6. **Файловая система** — не кладите всё в один markdown; используйте папки
7. **Не пишите очевидное** — сфокусируйтесь на нестандартном, специфичном знании
8. **Определяйте Output** — без формата нет предсказуемости и нет цепочек
