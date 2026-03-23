---
module: "04_skills"
lesson: 3
title: "Skills для context engineering"
type: "practice"
prerequisites: ["04_skills/lesson_02", "03_context_engineering/lesson_01"]
difficulty: "intermediate"
tags: ["skills", "context-engineering", "practice", "patterns"]
---

# Skills для context engineering

## Главный тезис

Context engineering — это дисциплина управления контекстным окном модели. Skills являются одним из основных инструментов context engineering: они позволяют **загружать знания по требованию**, а не держать всё в контексте постоянно. Существует целый класс Skills, специально спроектированных для оптимизации работы с контекстом.

---

## 1. Context Engineering: от промптов к системному управлению

### 1.1 Определение

Context engineering — это дисциплина курирования **всей информации**, которая попадает в контекстное окно модели:

- System prompts
- Tool definitions
- Извлечённые документы (RAG)
- История сообщений
- Результаты вызовов инструментов

В отличие от prompt engineering, который фокусируется на формулировке инструкций, context engineering работает с **холистическим управлением** всем бюджетом внимания модели.

### 1.2 Фундаментальная проблема

Контекстные окна ограничены не просто количеством токенов, а **механикой внимания** (attention). По мере роста контекста модели демонстрируют предсказуемые паттерны деградации:

- **Lost-in-the-middle** — модель лучше помнит начало и конец контекста, но теряет информацию в середине
- **U-shaped attention** — кривая внимания имеет форму U, с провалом посередине
- **Attention scarcity** — каждый добавленный токен размывает внимание ко всем остальным

### 1.3 Цель context engineering

Найти **минимальный набор высокосигнальных токенов**, который максимизирует вероятность желаемого результата. Каждый токен в контексте должен «зарабатывать» своё место.

---

## 2. Как Skills реализуют context engineering

### 2.1 Progressive Disclosure как инструмент управления контекстом

Архитектура Skills с трёхуровневой загрузкой — это прямая реализация принципов context engineering:

| Принцип CE | Реализация в Skills |
|-----------|---------------------|
| Минимизация контекста | Метаданные — только ~100 токенов на Skill |
| Загрузка по необходимости | Инструкции загружаются при триггере |
| Offloading | Ресурсы читаются через bash, не в основном контексте |
| Релевантность | Semantic search по описаниям для выбора Skill |

### 2.2 Filesystem как контекст

Файловая система Skill — это расширенный контекст, доступный без потребления основного окна. Агент может:

- Прочитать файл, когда нужна конкретная информация
- Выполнить скрипт и получить результат
- Использовать шаблон для генерации выхода

Это паттерн **tool output offloading**: вместо хранения информации в контексте, агент знает, *где* её найти, и загружает по необходимости.

### 2.3 Skill как «индекс» знаний

Хорошо спроектированный SKILL.md работает как **индекс**: он содержит достаточно информации, чтобы агент понял, что доступно, и ссылки на детали:

```markdown
# Data Analysis Skill

## Available Functions (see scripts/helpers.py for full code)
- `fetch_events(start, end)` — events from analytics DB
- `compute_retention(users, period)` — retention metrics
- `compare_cohorts(a, b)` — statistical comparison

## Dashboards (see references/dashboards.md)
- Revenue: DASH-001
- Retention: DASH-002
- Funnel: DASH-003
```

Агент видит обзор (десятки токенов), а полный код и документацию загружает только когда нужно.

---

## 3. Skills для управления контекстом: каталог

Репозиторий «Agent Skills for Context Engineering» (Muratcan Koylan) представляет систематизированную коллекцию Skills, специально спроектированных для context engineering. Эти Skills организованы в четыре уровня.

### 3.1 Foundational Skills

Skills, формирующие базовое понимание контекста.

**context-fundamentals**
- Что такое контекст и его анатомия в агентных системах
- Триггеры: «understand context», «explain context windows», «design agent architecture»

**context-degradation**
- Паттерны деградации контекста: lost-in-middle, context poisoning, distraction, context clash
- Триггеры: «diagnose context problems», «fix lost-in-middle», «debug agent failures»

**context-compression**
- Стратегии сжатия контекста для длительных сессий
- Триггеры: «compress context», «summarize conversation», «reduce token usage»

### 3.2 Architectural Skills

Skills для проектирования архитектуры агентных систем.

**multi-agent-patterns**
- Паттерны: orchestrator, peer-to-peer, hierarchical
- Триггеры: «design multi-agent system», «implement supervisor pattern»

**memory-systems**
- Short-term, long-term и graph-based memory
- Триггеры: «implement agent memory», «build knowledge graph», «track entities»

**tool-design**
- Проектирование инструментов, которые агенты используют эффективно
- Триггеры: «design agent tools», «reduce tool complexity», «implement MCP tools»

**filesystem-context**
- Использование файловой системы для dynamic context discovery, offloading и plan persistence
- Триггеры: «offload context to files», «dynamic context discovery», «agent scratch pad»

**hosted-agents**
- Фоновые coding-агенты с sandboxed VM, pre-built images, multiplayer support
- Триггеры: «build background agent», «sandboxed execution»

### 3.3 Operational Skills

Skills для оптимизации работающих систем.

**context-optimization**
- Compaction, masking и caching стратегии
- Триггеры: «optimize context», «reduce token costs», «implement KV-cache»

**evaluation / advanced-evaluation**
- Фреймворки оценки агентных систем, включая LLM-as-a-Judge
- Триггеры: «evaluate agent performance», «implement LLM-as-judge»

### 3.4 Development Methodology

**project-development**
- Полный цикл LLM-проекта: от идеи до деплоя
- Task-model fit analysis, pipeline architecture, structured output design
- Триггеры: «start LLM project», «design batch pipeline»

### 3.5 Cognitive Architecture

**bdi-mental-states**
- Преобразование внешнего RDF-контекста в ментальные состояния агента (beliefs, desires, intentions) по формальной BDI-онтологии
- Триггеры: «model agent mental states», «implement BDI architecture»

---

## 4. Паттерны context-aware Skills

### 4.1 Паттерн: Context Budget Manager

Skill, который помогает агенту **отслеживать** расход контекстного бюджета:

```markdown
---
name: context-budget
description: Track and optimize context window usage. Use when
  conversation is getting long or agent seems to lose context.
---

# Context Budget Manager

## Purpose
Monitor context usage and apply compression when needed.

## Instructions
1. Check current context usage estimate
2. If > 70% capacity, identify low-value content for removal
3. Apply compaction: summarize old messages, remove tool outputs
4. Log decisions in `context-log.jsonl`

## Non-Negotiable Acceptance Criteria
- [ ] Context usage stays below 80% capacity
- [ ] Critical information is never removed
- [ ] Compression decisions are logged
```

### 4.2 Паттерн: Dynamic Context Discovery

Skill, использующий файловую систему для обнаружения контекста на лету:

```markdown
---
name: codebase-navigator
description: Discover and load relevant code context dynamically.
  Use when working with unfamiliar parts of the codebase.
---

# Codebase Navigator

## Instructions
1. Map the project structure to understand organization
2. Use `scripts/find-related.py <file>` to discover related files
3. Load only the files directly relevant to the current task
4. Store navigation map in `scratch/nav-map.json` for reuse

## Available Resources
- `scripts/find-related.py` — finds files related by imports/references
- `scripts/summarize-module.py` — creates a brief summary of a module
- `scratch/` — working directory for temporary context artifacts
```

### 4.3 Паттерн: Scratch Pad / Plan Persistence

Skill, использующий файловую систему как «блокнот» для сохранения плана и промежуточных результатов:

```markdown
---
name: task-planner
description: Create and persist execution plans for complex tasks.
  Use for multi-step tasks that may exceed single-turn context.
---

# Task Planner

## Instructions
1. Decompose the task into numbered steps
2. Write plan to `scratch/plan.md`
3. Execute steps, marking each as complete in the plan file
4. If context gets long, re-read `scratch/plan.md` to regain focus

## Non-Negotiable Acceptance Criteria
- [ ] Plan is written to file before execution starts
- [ ] Each step is marked as complete/failed in the plan
- [ ] Final status summary is appended to plan
```

Этот паттерн критически важен для **длинных задач**: даже если модель «забывает» промежуточные шаги из-за attention degradation, она может перечитать план из файла.

### 4.4 Паттерн: Context Compression

Skill для управления длительными сессиями через сжатие:

```markdown
---
name: session-compressor
description: Compress long conversation history to maintain
  agent effectiveness. Use when session exceeds 50 messages.
---

# Session Compressor

## Instructions
1. Identify messages that can be safely summarized
2. Group related tool calls and their outputs
3. Replace verbose outputs with summaries
4. Preserve: user intent, decisions made, current state

## Compression Strategies (see references/strategies.md)
- Tool output reduction: keep only final result, not intermediate steps
- Message grouping: combine related exploration into summary
- Decision log: extract key decisions into compact format
```

### 4.5 Паттерн: Memory-Augmented Skill

Skill, который поддерживает долговременную память через файлы:

```markdown
---
name: entity-tracker
description: Track entities (users, services, APIs) across sessions.
  Use when working with complex systems with many components.
---

# Entity Tracker

## Instructions
1. On task start, load `data/entities.jsonl`
2. During work, update entity records with new information
3. On task completion, append changes to `data/entities.jsonl`

## Data Format
Each line in entities.jsonl:
{"name": "...", "type": "...", "properties": {...}, "last_updated": "..."}

## Non-Negotiable Acceptance Criteria
- [ ] No entity information is lost between sessions
- [ ] Contradictions are flagged, not silently overwritten
```

Паттерн append-only JSONL-файлов с schema-first lines хорошо работает для agent-friendly парсинга данных.

---

## 5. Принципы проектирования context-aware Skills

### 5.1 Platform Agnosticism

Skills для context engineering должны фокусироваться на **переносимых принципах**, а не на vendor-specific реализациях. Паттерны работают одинаково в Claude Code, Cursor, и любой другой агентной платформе, поддерживающей skills или custom instructions.

### 5.2 Правило SKILL.md < 500 строк

Для оптимальной производительности SKILL.md не должен превышать 500 строк. Всё, что длиннее, должно быть вынесено в reference-файлы. Это прямое следствие принципов context engineering — основной файл должен помещаться в контекст без деградации.

### 5.3 Conceptual Foundation + Practical Examples

Лучшие Skills для context engineering сочетают:
- **Концептуальную основу** — почему этот подход работает
- **Практические примеры** — Python pseudocode, работающий без специфических зависимостей

Скрипты и примеры демонстрируют концепции, но не требуют конкретных установок.

### 5.4 Триггеры должны быть конкретными

Каждый context engineering Skill должен иметь чёткие триггеры в описании:

```yaml
# Плохо
description: Helps with context management

# Хорошо
description: Diagnose and fix context degradation patterns including
  lost-in-middle, attention scarcity, and context poisoning. Use when
  agent responses degrade in long sessions or miss relevant information.
```

---

## 6. Context Engineering через композицию Skills

### 6.1 Многоуровневая архитектура

Context engineering Skills работают на разных уровнях абстракции:

```
Уровень 3: Task-specific Skills
  (pr-review, data-analysis, deploy-service)
          ↓ используют
Уровень 2: Architectural Skills
  (memory-systems, multi-agent-patterns, tool-design)
          ↓ опираются на
Уровень 1: Foundational Skills
  (context-fundamentals, context-degradation, context-compression)
```

Каждый уровень строится на знаниях предыдущего. Task-specific Skill может использовать паттерны из architectural Skills, которые реализуют принципы из foundational Skills.

### 6.2 Skill как plugin

В Claude Code репозитории Skills могут выступать как **Plugin Marketplace** — коллекции Skills, которые агент автоматически обнаруживает и активирует в зависимости от контекста задачи.

Установка marketplace:
```
/plugin marketplace add <repo>
```

Установка конкретного plugin:
```
/plugin install context-engineering-fundamentals@context-engineering-marketplace
```

Доступные plugin-бандлы:

| Plugin | Skills |
|--------|--------|
| `context-engineering-fundamentals` | context-fundamentals, context-degradation, context-compression, context-optimization |
| `agent-architecture` | multi-agent-patterns, memory-systems, tool-design, filesystem-context, hosted-agents |
| `agent-evaluation` | evaluation, advanced-evaluation |
| `agent-development` | project-development |
| `cognitive-architecture` | bdi-mental-states |

### 6.3 Пример композиции: Digital Brain

Пример проекта «Digital Brain» демонстрирует комплексное применение context engineering Skills:

- **Progressive Disclosure**: 3 уровня загрузки (SKILL.md → MODULE.md → data files)
- **Module Isolation**: 6 независимых модулей (identity, content, knowledge, network, operations, agents)
- **Append-Only Memory**: JSONL-файлы со schema-first строками для agent-friendly парсинга
- **Automation Scripts**: 4 консолидированных инструмента (weekly_review, content_ideas, stale_contacts, idea_to_draft)

Каждое архитектурное решение в этом проекте трассируется к конкретному принципу из context engineering Skills.

---

## 7. Антипаттерны context engineering в Skills

### 7.1 Загрузка всего в контекст

**Антипаттерн**: поместить всю документацию API в SKILL.md.

**Решение**: оставить в SKILL.md обзор и ссылки, детали — в `references/`.

### 7.2 Отсутствие offloading

**Антипаттерн**: хранить все промежуточные результаты в контексте сообщений.

**Решение**: писать промежуточные результаты в файлы (`scratch/`), перечитывать когда нужно.

### 7.3 Игнорирование attention patterns

**Антипаттерн**: поместить важную информацию в середину длинного SKILL.md.

**Решение**: критическая информация — в начале и в конце. Non-Negotiable Acceptance Criteria — ближе к концу (last-token advantage).

### 7.4 Монолитные Skills

**Антипаттерн**: один Skill на 1000+ строк, покрывающий весь рабочий процесс.

**Решение**: декомпозиция на несколько Skills по принципу single responsibility. Каждый Skill < 500 строк.

---

## 8. Практическое упражнение

### Задание

Спроектируйте context-aware Skill для вашего рабочего процесса:

1. Выберите повторяющуюся задачу, которую вы делаете минимум раз в неделю
2. Определите, какая информация нужна для этой задачи
3. Разделите информацию на уровни progressive disclosure:
   - Что агент должен знать всегда? (→ description)
   - Что нужно при запуске? (→ SKILL.md body)
   - Что нужно иногда? (→ reference files)
   - Что агент может получить, выполнив скрипт? (→ scripts/)
4. Напишите SKILL.md с 5 обязательными секциями
5. Определите, нужна ли этому Skill память (файловое хранение данных между сессиями)
6. Протестируйте и добавьте первые Gotchas

### Критерии оценки

- Описание содержит чёткие триггеры
- Инструкции — не более 3 шагов
- Есть Non-Negotiable Acceptance Criteria
- Output формат определён
- Информация распределена по уровням progressive disclosure
- SKILL.md < 500 строк

---

## Итоги

1. **Context engineering** — управление всем контекстным окном, не только промптом
2. **Skills** реализуют CE через progressive disclosure и filesystem offloading
3. Существует каталог CE-специализированных Skills: от context-fundamentals до cognitive architecture
4. Ключевые паттерны: context budget, dynamic discovery, scratch pad, compression, memory
5. **SKILL.md < 500 строк** — критическое правило для эффективности
6. Skills компонуются в многоуровневые архитектуры: foundational → architectural → task-specific
7. Антипаттерны: монолитные Skills, загрузка всего в контекст, игнорирование attention patterns
