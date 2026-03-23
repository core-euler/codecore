---
module: "01_foundations"
lesson: 2
title: "Хуки, субагенты и расширение агентного цикла"
type: "theory"
prerequisites: ["01_foundations/lesson_01"]
difficulty: "beginner"
tags: ["hooks", "subagents", "claude-code", "event-control"]
---

# Модуль 1, Подмодуль 2: Хуки, субагенты и расширение агентного цикла

## Введение

Claude Code — это не просто инструмент для выполнения команд, а полноценная агентная система, которая может планировать, выполнять задачи и корректировать свои действия на основе результатов. Однако для того чтобы адаптировать это поведение под конкретные потребности проекта, необходимо понимать два ключевых механизма расширения: **хуки** (hooks) для перехвата и контроля событий в агентном цикле, и **субагенты** (subagents) для параллелизации работы и изоляции контекста.

В этом подмодуле мы разберем архитектуру этих двух систем, изучим их интеграцию друг с другом и рассмотрим практические паттерны их использования.

---

## 1. Хуки: расширение агентного цикла через пользовательский код

### 1.1. Что такое хуки и зачем они нужны

Хук (hook) — это пользовательский обработчик события, который срабатывает в определенных точках жизненного цикла Claude Code. Вместо того чтобы переписывать основную логику агента, вы можете подключить свой код на определенных этапах:

- **Перехватить действия** — например, заблокировать опасную команду перед ее выполнением
- **Логировать события** — записать информацию о том, что произошло во время сессии
- **Запустить дополнительные проверки** — вызвать линтер, тесты или pre-commit скрипты
- **Интегрировать с внешними сервисами** — отправить уведомление, запустить CI/CD пайплайн
- **Трансформировать данные** — изменить входные или выходные данные перед обработкой

Хуки работают на трех уровнях абстракции:

1. **Shell-команды (Command hooks)** — простые скрипты на bash/sh, которые читают JSON из stdin
2. **HTTP-эндпоинты (HTTP hooks)** — отправляют JSON POST запрос на внешний сервер
3. **LLM-промпты (Prompt hooks)** — обрабатывают событие через другой LLM API вызов

### 1.2. Жизненный цикл хуков: основные события

Claude Code генерирует события в следующих точках:

| Событие | Когда срабатывает |
|---|---|
| `SessionStart` | Начало сессии или восстановление после перерыва |
| `UserPromptSubmit` | Пользователь отправляет промпт, перед обработкой Claude |
| `PreToolUse` | **Перед** выполнением инструмента (может заблокировать) |
| `PermissionRequest` | Появляется диалог разрешения (файловые операции, сеть) |
| `PostToolUse` | **После** успешного выполнения инструмента |
| `PostToolUseFailure` | **После** ошибки при выполнении инструмента |
| `Notification` | Claude отправляет уведомление пользователю |
| `SubagentStart` | Запущена работа субагента |
| `SubagentStop` | Субагент завершил работу |
| `Stop` | Claude завершает ответ (конец цикла рассуждения) |
| `InstructionsLoaded` | Загружен файл правил из `.claude/rules/*.md` |
| `ConfigChange` | Изменена конфигурация сессии |
| `WorktreeCreate` / `WorktreeRemove` | Создано/удалено git worktree для изоляции |
| `SessionEnd` | Конец сессии |

### 1.3. Архитектура системы хуков: конфигурация и Matchers

Хуки конфигурируются в файле `.claude/hooks.json` в корне проекта или в `.claude/settings.json`. Базовая структура определяет события и обработчики:

> **Удалено:** Полная конфигурация хуков в JSON. Структура включает события (PreToolUse, PostToolUse и т.д.), в каждом из которых массив обработчиков с matcher (фильтр инструментов), типом (command/http/prompt) и timeout.

**Matcher** — это фильтр, определяющий, для каких инструментов срабатывает хук:

- `"*"` — все инструменты
- `"Bash"` — конкретный инструмент
- `["Bash", "Write"]` — несколько инструментов
- `"/grep|find/"` — регулярное выражение

Три типа обработчиков:

1. **`"command"`** — shell-скрипт (самый быстрый и надежный)
2. **`"http"`** — HTTP endpoint (для интеграции с внешними сервисами)
3. **`"prompt"`** — LLM-промпт (для сложной логики)

### 1.4. Структура данных в хуках: вход и выход

Каждый хук получает **JSON структуру на входе** с информацией о событии и должен вернуть **JSON ответ**.

**Типичная структура входных данных:**

```json
{
  "tool": "Bash",
  "input": {
    "command": "command_text"
  },
  "context": {
    "userId": "user123",
    "sessionId": "sess_abc",
    "timestamp": "ISO8601"
  }
}
```

**Типичная структура выходных данных (для PreToolUse):**

```json
{
  "decision": "allow" | "block" | "ask",
  "reason": "Human-readable explanation",
  "suggestion": "Optional suggestion for fix"
}
```

**Exit codes для Command Hooks:**
- `0` — успех (для PreToolUse = разрешить, для PostToolUse = логирование прошло)
- `1` — ошибка, но не критичная
- `2` — критическая блокировка (для PreToolUse = не выполнять инструмент)

**Основные события и их структуры данных:**

| Событие | Входные данные | Выходные данные | Использование |
|---------|---|---|---|
| **PreToolUse** | tool, input, context | decision (allow/block/ask) | Валидация перед выполнением |
| **PostToolUse** | tool, input, result | logged, notification | Логирование после выполнения |
| **SubagentStart** | agent, sessionId, prompt | approval | Контроль запуска субагента |
| **SubagentStop** | agent, sessionId, result | — | Реагирование на завершение |
| **PermissionRequest** | tool, action, target | decision | Контроль доступа к файлам |

### 1.5. Типы обработчиков: Command, HTTP и Prompt

#### 1.5.1. Command Hooks (Shell-скрипты)

**Command hooks** — самый быстрый и надежный тип. Скрипт на bash/sh получает JSON на stdin, обрабатывает его и возвращает JSON + exit code.

**Когда использовать Command Hooks:**
- Простые проверки (валидация команды по паттерну)
- Логирование в файл или систему
- Быстрые операции (< 1 сек)
- Когда нужна надежность (не зависит от внешних сервисов)

**Конфигурация:**

> **Удалено:** Пример конфигурации Command Hook в JSON. Она содержит путь скрипта (/usr/local/bin/validate-bash.sh), timeout (2000ms) и matcher для фильтрации инструментов (например, только Bash).

**Паттерн реализации Command Hook:**
1. Скрипт читает JSON из stdin
2. Парсит JSON (обычно с помощью `jq`)
3. Выполняет логику (валидация, логирование, трансформация)
4. Выводит JSON результат на stdout
5. Выходит с правильным exit code

**Пример логики валидации:**
- Проверить команду на опасные паттерны (rm -rf, DROP TABLE, fork bomb)
- Проверить SQL запрос на injection паттерны
- Проверить пути файлов на доступность
- Проверить переменные окружения
exit 0
```

**Преимущества:**
- Минимальная задержка (no network overhead)
- Полный контроль над окружением
- Легко отлаживать локально

**Недостатки:**
- Зависит от ОС (bash/sh)
- Сложнее для сложной логики

#### 1.5.2. HTTP Hooks (Внешние API)

**HTTP hooks** используют для интеграции с облачными сервисами, вебхуками или сложной бизнес-логикой. Claude Code отправляет POST запрос на ваш сервер с JSON данными о событии.

**Когда использовать HTTP Hooks:**
- Интеграция с внешними сервисами (Slack, PagerDuty, DataDog)
- Сложная бизнес-логика (валидация против БД)
- Централизованное логирование
- CI/CD интеграция (запуск тестов, deploy'ы)

**Конфигурация:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": ["Write", "Edit"],
        "http": "https://webhook.company.com/claude-hooks",
        "timeout": 10000,
        "retries": 3
      }
    ]
  }
}
```

**Что отправляется на HTTP endpoint:**

POST запрос с JSON телом:
- **tool** — имя инструмента (Bash, Write, etc.)
- **input** — параметры инструмента
- **result** — результат выполнения (stdout, exitCode, etc.)
- **context** — контекст (sessionId, userId, timestamp)
- Заголовок `X-Claude-Session-ID` для идентификации

**Типичные HTTP hook интеграции:**
- **Slack интеграция** — отправить сообщение в канал "#agent-logs"
- **CI/CD интеграция** — запустить тесты если изменился код
- **Аудит логирование** — отправить в централизованную систему логирования
- **Мониторинг** — отправить метрику в DataDog, Prometheus
- **Апрувалы** — отправить на апрув человеку перед важными операциями

**Преимущества HTTP Hooks:**
- Мощная интеграция с внешними сервисами
- Можно реализовать на любом языке
- Асинхронные операции возможны

**Недостатки:**
- Сетевая задержка (10-100ms)
- Требует работающего внешнего сервера
- Сложнее тестировать и отлаживать

#### 1.5.3. Prompt Hooks (LLM-обработка)

**Prompt hooks** используют LLM API для обработки события. Максимально мощно для анализа и аналитики, но медленно и дорого.

**Когда использовать Prompt Hooks:**
- Сложная аналитика результатов (анализ логов, ошибок)
- Автоматическое улучшение кода (code review, suggestions)
- Качественная фильтрация (определить, важное ли событие)
- Генерация конспектов и резюме

**Конфигурация:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "prompt": "Analyze this bash output and identify any issues or performance concerns",
        "model": "claude-haiku",
        "timeout": 30000
      }
    ]
  }
}
```

**Как работает Prompt Hook:**

Claude Code формирует промпт вроде:
```
Tool: Bash
Command: npm test
Output:
FAIL - 3 tests failed out of 42
...

Analyze this execution and provide insights.
```

Затем отправляет в LLM API и ждет ответа.

**Примеры использования:**
- **Code review** — "Найти проблемы безопасности в этом коде"
- **Performance анализ** — "Есть ли bottlenecks в логах?"
- **Categorization** — "Это ошибка пользователя или баг системы?"

**Преимущества Prompt Hooks:**
- Сложная контекстная логика
- Естественный язык анализ
- Адаптируется к новым паттернам

**Недостатки:**
- Самый медленный (500-2000ms за запрос)
- Дорогой (дополнительные API вызовы)
- Недетерминирован (разные ответы для одинакового input)

### 1.6. Асинхронные хуки и параллельное выполнение

По умолчанию хуки выполняются **синхронно** — Claude Code ждет результата перед продолжением. Для длительных операций можно сделать их асинхронными:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "http": "https://analytics.company.com/log",
        "async": true,
        "timeout": 30000
      }
    ]
  }
}
```

**При `"async": true`:**
- Claude Code не ждет ответа от хука
- Результат хука не блокирует выполнение агента
- Ошибки хука не влияют на сессию
- Идеально для логирования, аналитики и уведомлений

**Сравнение синхронных и асинхронных хуков:**

| Аспект | Синхронный | Асинхронный |
|--------|-----------|-----------|
| **Блокирует ли агент** | Да | Нет |
| **Может ли отклонить действие** | Да (PreToolUse) | Нет |
| **Примеры** | Валидация | Логирование, уведомления |
| **Таймаут** | Критичен (замораживает агент) | Некритичен |

### 1.7. MCP Tool Hooks: специальная поддержка

Для инструментов из MCP (Model Context Protocol) можно настроить специфичные хуки:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "MCP:slack",
        "command": "validate-slack-message.sh"
      }
    ]
  }
}
```

Где `MCP:slack` — это инструмент из MCP сервера Slack. Можно валидировать сообщения перед отправкой.

### 1.8. Timeout и обработка ошибок

Каждый хук имеет параметр `timeout` (в миллисекундах). При таймауте:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "validate.sh",
        "timeout": 5000,
        "onTimeout": "allow"
      }
    ]
  }
}
```

**Опции обработки таймаута:**
- `"onTimeout": "allow"` — если хук не ответил за 5 сек, разрешить инструмент (default)
- `"onTimeout": "block"` — заблокировать инструмент при таймауте
- `"onTimeout": "ignore"` — просто проигнорировать результат хука

**Best practice:** для синхронных PreToolUse хуков используйте маленькие timeouts (2-5 сек), так как они блокируют агента.

### 1.9. Практические сценарии использования хуков

**Сценарий 1: Валидация перед написанием файла**
- PreToolUse перехватывает Write/Edit инструменты
- Command hook проверяет путь файла (не тестовые файлы)
- Проверяет синтаксис JSON/YAML
- Блокирует если формат невалидный

**Сценарий 2: Логирование и аудит всех действий**
- PostToolUse хук для всех инструментов ("*")
- HTTP hook отправляет в централизованную систему логирования
- Асинхронный (async: true) чтобы не замораживать агент
- Включает timestamp, userId, sessionId

**Сценарий 3: Автоматическое улучшение кода**
- PostToolUse для Edit инструмента
- Prompt hook запускает code review через LLM
- Предлагает улучшения (перформанс, безопасность, стиль)
- Агент может использовать этот feedback для следующей итерации
    "PostToolUse": [
      {
        "matcher": ["Write", "Edit"],
        "command": "scripts/post-write-checks.sh",
        "timeout": 10000
      }
    ]
  }
}
```

**Файл `scripts/pre-write-validation.sh`:**

> **Удалено:** Bash скрипт валидации перед записью файла. Скрипт читает JSON входные данные (путь файла, содержимое), проверяет не защищённый ли это файл (package.json, .env и т.д.), и возвращает JSON решение (allow/block/ask). Использует jq для парсинга.

**Файл `scripts/post-write-checks.sh`:**

> **Удалено:** Bash скрипт логирования и форматирования после записи. Скрипт проверяет exit code инструмента, если успешно, то запускает форматер (black для Python, prettier для TypeScript) и отправляет событие в систему мониторинга через curl.



### 1.10. Exit codes и их поведение в разных событиях

| Event | Exit 0 | Exit 1 | Exit 2 |
|---|---|---|---|
| `PreToolUse` | Разрешить | Ошибка (инструмент не выполняется) | Блокировать |
| `PostToolUse` | Продолжить | Ошибка логирования | N/A |
| `UserPromptSubmit` | Продолжить | Ошибка | Отклонить промпт |
| `PermissionRequest` | Разрешить | Ошибка | Отклонить |

---

## 2. Субагенты: параллелизация и изоляция контекста

### 2.1. Архитектура субагентов: чему они нас учат

Вместо одного мощного агента, который последовательно выполняет все задачи в одном контексте, Claude Code позволяет запускать **параллельные субагенты** с независимыми контекстами. Это решает несколько проблем:

**Проблема 1: Контекстное загрязнение**
```
Сценарий: Claude Code анализирует кодовую базу (1000 файлов)
→ Контекст заполняется информацией о файлах
→ Остается мало места для рассуждений о новой задаче
→ Качество ответов падает
```

**Решение: Explore субагент (встроенный)**
```
Главный агент: "Помогите спланировать новую функцию"
↓
Claude Code автоматически запускает Explore субагент:
  - Читает файлы (контекст изолирован)
  - Возвращает только релевантную информацию
  - Основной контекст остается чистым
↓
Главный агент получает только краткий отчет
```

**Проблема 2: Параллелизм требует координации**
```
Сценарий: Нужно добавить 3 независимые функции
→ Если делать последовательно: 30 минут
→ Если делать параллельно: 10 минут (но как координировать?)
```

**Решение: Task tool (fan-out/fan-in паттерн)**
```
Главный агент: "Добавьте три функции параллельно"
↓
├─ Субагент 1: Добавляет функцию A (в изолированном контексте)
├─ Субагент 2: Добавляет функцию B (независимо)
└─ Субагент 3: Добавляет функцию C (без конфликтов)
↓
Главный агент собирает результаты и интегрирует их
```

### 2.2. Task tool и запуск подзадач

Главный механизм запуска субагентов — это **Task tool**. Когда Claude Code видит, что нужно запустить подзадачу, он может использовать:

```
Task(description, model="opus", tools=["Bash", "Read"])
```

При вызове Task:
1. Создается новый **изолированный контекст** для субагента
2. Субагент получает описание задачи и выбранные инструменты
3. Субагент работает **параллельно** (если включен background mode)
4. Результат возвращается в основной контекст

**Пример из документации:**

Основной агент (выполняется в главной сессии):
```
Пользователь: "Исправьте баги в трех компонентах одновременно"

Claude рассуждает:
→ Это три независимые задачи
→ Запускаю три субагента параллельно
→ Жду результатов
→ Интегрирую исправления

Task("Fix bug in ComponentA and run tests") → SubagentA
Task("Fix bug in ComponentB and run tests") → SubagentB
Task("Fix bug in ComponentC and run tests") → SubagentC

[Все три работают параллельно]

Результаты:
- SubagentA: "Fixed issue with state management, all tests pass"
- SubagentB: "Fixed prop validation, coverage increased to 95%"
- SubagentC: "Fixed memory leak, performance improved by 20%"

Claude интегрирует все изменения в main контекст
```

### 2.3. Встроенные субагенты

Claude Code предоставляет три встроенных специализированных субагента:

#### 2.3.1. Explore Subagent (быстрый анализ кодовой базы)

**Характеристики:**
- **Модель**: Haiku (самая быстрая)
- **Инструменты**: Только read-only (Glob, Grep, Read)
- **Цель**: Быстрый поиск файлов и анализ структуры

**Когда используется:**
```
Пользователь: "Где в коде обрабатывается аутентификация?"

Claude автоматически использует Explore:
→ Быстро ищет файлы содержащие "auth"
→ Анализирует структуру
→ Возвращает в основной контекст список релевантных файлов
```

**Конфигурация thorough level:**
```json
{
  "explorationDepth": "very-thorough"
}
```

#### 2.3.2. Plan Subagent (планирование сложных задач)

**Характеристики:**
- **Модель**: Opus (самая мощная)
- **Инструменты**: Только read-only + Bash для выполнения команд (без изменения файлов)
- **Цель**: Сложное планирование и анализ

**Когда используется:**
```
Пользователь: "Спланируйте архитектуру системы для обработки 1М событий в день"

Claude использует Plan:
→ Анализирует текущую архитектуру
→ Разрабатывает 3 варианта решения
→ Оценивает трadeoffs
→ Возвращает детальный план
```

#### 2.3.3. General-Purpose Subagent (универсальный)

**Характеристики:**
- **Модель**: Sonnet (баланс speed/capability)
- **Инструменты**: Все инструменты (как в главной сессии)
- **Цель**: Выполнение независимых задач

### 2.4. Создание пользовательских субагентов

Субагенты определяются в файлах с YAML frontmatter. Место сохранения определяет scope:

**Места размещения субагентов:**

```
.claude/agents/        → Проектный уровень (версионируется в git)
~/.claude/agents/      → Пользовательский уровень (все проекты)
CLI флаг --agents      → Сессионный уровень (JSON at runtime)
```

**Структура YAML frontmatter:**

```yaml
---
name: code-reviewer
description: "Проверяет код на качество и безопасность"
model: "claude-opus-4-6"  # модель для этого субагента
tools:
  - Read        # выбираем, какие инструменты доступны
  - Grep
  - Bash
maxTurns: 10    # максимум итераций для субагента
permissionMode: "auto"  # как обрабатывать разрешения
---
```

**Что можно настроить для субагента:**

| Параметр | Значение | Назначение |
|----------|----------|-----------|
| **model** | haiku, sonnet, opus | Баланс скорость/качество |
| **tools** | [список] | Какие инструменты доступны |
| **maxTurns** | число | Максимум итераций (защита от циклов) |
| **permissionMode** | auto, dontAsk, ask | Как обрабатывать разрешения |
| **temperature** | 0.0-1.0 | Креативность субагента |
| **contextDepth** | shallow, normal, deep | Сколько контекста передавать |

**Типичные конфигурации субагентов:**

1. **Fast Explorer** — быстрый анализ файлов
   - Model: Haiku
   - Tools: Read, Grep, Glob (только чтение)
   - maxTurns: 3-5

2. **Code Reviewer** — глубокий анализ кода
   - Model: Opus
   - Tools: Read, Grep (только чтение)
   - maxTurns: 10-15

3. **General Worker** — выполнение независимых задач
   - Model: Sonnet
   - Tools: Все инструменты
   - maxTurns: 20-30
  - Fix: ...

## Major Issues
- Issue 1
  - Severity: performance/maintainability/other
  - Suggestion: ...

## Minor Issues
- Issue 1

## Strengths
- Positive aspect 1
- Positive aspect 2

## Summary
Overall assessment and recommended next steps.
```

Запуск этого субагента:

```
Пользователь: "Проверьте файл src/database.ts на качество кода"

Claude:
→ Определяет, что это review задача
→ Автоматически использует code-reviewer субагент
→ Субагент анализирует файл (в изолированном контексте)
→ Возвращает детальный review
```

### 2.5. Конфигурация субагентов: полный набор параметров

**Frontmatter параметры:**

```yaml
---
name: database-analyzer
description: Analyze and optimize database queries and schemas
model: sonnet                    # opus, sonnet, haiku, или inherit
tools:                           # Allowlist инструментов
  - Bash
  - Read
  - Write
disallowedTools:                # Denylist инструментов
  - Edit                        # Запретить Edit
permissionMode: acceptEdits      # default, acceptEdits, dontAsk, bypassPermissions, plan
maxTurns: 20                    # Максимум turns для субагента
skills:                         # Preload скиллы в контекст
  - sql-optimization
  - performance-analysis
mcpServers:                     # MCP сервера для субагента
  postgresql:
    command: docker
    args: ["run", "-p", "5432:5432"]
hooks:                          # Хуки для этого субагента
  PreToolUse:
    - matcher: Bash
      command: validate-sql.sh
memory: project                 # user, project, или local (persistent memory)
background: false               # true = всегда запускать в фоне
isolation: worktree             # worktree = использовать git worktree
---
```

### 2.6. Worktree Isolation: полная изоляция git состояния

Когда субагент имеет `isolation: worktree`, он получает **полностью отдельную копию репозитория**:

```yaml
---
name: feature-branch-worker
isolation: worktree
---
```

**Как это работает:**

```
Главный репозиторий (main branch)
├── file1.py
├── file2.py
└── .git/

Субагент запускается:
↓
git worktree create .git/worktrees/subagent-abc
├── file1.py (копия)
├── file2.py (копия)
└── .git (symlink to main)

Субагент работает:
- Создает новый branch
- Коммитит изменения
- Запускает тесты
- БЕЗ влияния на main branch

После завершения:
- Если нет изменений: worktree удаляется
- Если есть изменения: можно merge в main
```

**Пример использования: параллельная разработка функций**

```json
{
  "agents": [
    {
      "name": "feature-auth",
      "isolation": "worktree",
      "description": "Implement new authentication system"
    },
    {
      "name": "feature-api",
      "isolation": "worktree",
      "description": "Build REST API v2"
    },
    {
      "name": "feature-ui",
      "isolation": "worktree",
      "description": "Redesign user interface"
    }
  ]
}
```

Три субагента одновременно работают в разных worktrees:
```
Текущее время: 10:00
- Main branch: stable (tests pass)
- worktree/feature-auth: development (new code)
- worktree/feature-api: development (new code)
- worktree/feature-ui: development (new code)

Время: 10:30
- Main branch: все еще stable
- worktree/feature-auth: complete, ready for merge
- worktree/feature-api: 80% complete
- worktree/feature-ui: 50% complete

Main branch интегрирует feature-auth без влияния на других
```

### 2.7. Паттерны использования субагентов

#### 2.7.1. Fan-out / Fan-in паттерн

Разбиваем одну задачу на несколько параллельных подзадач:

```
Задача: "Мигрируйте базу данных с PostgreSQL на MongoDB"

Fan-out (распределение):
├─ Субагент 1: Создать MongoDB схему
├─ Субагент 2: Написать миграционный скрипт для Users таблицы
├─ Субагент 3: Написать миграционный скрипт для Orders таблицы
└─ Субагент 4: Написать миграционный скрипт для Analytics таблицы

[Все работают параллельно в течение 2 часов]

Fan-in (сбор результатов):
Главный агент:
✓ Проверяет все миграции
✓ Интегрирует их в один файл
✓ Запускает полный тест
✓ Создает документацию
```

**Код для Claude:**

```
Я запускаю миграцию с параллелизмом:

1. Создайте MongoDB схему (Субагент A)
2. Мигрируйте Users данные (Субагент B)
3. Мигрируйте Orders данные (Субагент C)
4. Мигрируйте Analytics данные (Субагент D)

После завершения всех четырех:
5. Проверьте integrity между таблицами
6. Запустите full test suite
7. Создайте миграционный отчет
```

#### 2.7.2. Pipeline паттерн

Последовательная передача результатов между субагентами:

```
Входные данные (сырые логи)
↓
Субагент 1: Парсинг и нормализация
↓
Субагент 2: Анализ и агрегация
↓
Субагент 3: Визуализация и отчет
↓
Итоговый отчет
```

**Пример: анализ логов приложения**

```
Task 1: "Parse raw logs from /var/log/app.log.
Extract: timestamp, level, message, component.
Return CSV."

[Результат: normalized_logs.csv]

Task 2: "Read normalized_logs.csv and analyze:
- Error rate by component
- Top 10 errors
- Time-based distribution
Return JSON with statistics"

[Результат: analysis.json]

Task 3: "Create HTML dashboard from analysis.json
with charts and summary. Save to reports/dashboard.html"

[Результат: dashboard.html готов для пользователя]
```

#### 2.7.3. Specialist Delegation паттерн

Разные субагенты специализируются на разных задачах:

```
Главный агент (оркестратор):
- Читает requirements
- Определяет тип задачи
- Делегирует нужному специалисту

Backend-specialist (субагент):
- инструменты: Bash, Read, Write (API/database только)
- model: opus
- skill: backend-architecture

Frontend-specialist (субагент):
- инструменты: Bash, Read, Write (UI/CSS only)
- model: sonnet
- skill: frontend-design

DevOps-specialist (субагент):
- инструменты: Bash, Docker (инструменты)
- model: haiku
- skill: infrastructure
```

### 2.8. Persistent Memory для субагентов

Субагент может иметь память, которая сохраняется между сессиями:

```yaml
---
name: architectural-advisor
description: Learn and advise on project architecture
memory: project
---
```

Субагент автоматически получает доступ к `.claude/agent-memory/architectural-advisor/`:

```
.claude/agent-memory/architectural-advisor/
├── MEMORY.md (первые 200 строк инъектируются в промпт)
├── decisions.md (архитектурные решения)
├── patterns.md (выявленные паттерны)
└── learnings.md (накопленные знания)
```

**Как это работает:**

```
Первая сессия:
- Субагент анализирует архитектуру
- Пишет в MEMORY.md: "Проект использует микросервис архитектуру"
- Пишет в decisions.md: "Выбрана PostgreSQL для основной БД"

Вторая сессия (месяц спустя):
- Субагент читает MEMORY.md (уже знает микросервис архитектуру)
- Быстро предлагает улучшения, основываясь на прошлом опыте
- Обновляет MEMORY.md с новыми решениями
```

### 2.9. Hooks для субагентов

Субагенты могут иметь свои собственные хуки (срабатывают только во время работы субагента):

**В frontmatter субагента (локальные хуки):**

```yaml
---
name: secure-database-agent
hooks:
  PreToolUse:
    - matcher: Bash
      command: validate-sql-operations.sh
  PostToolUse:
    - matcher: Bash
      command: log-database-changes.sh
---
```

**В главной сессии `.claude/settings.json` (глобальные хуки для субагентов):**

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "database-agent",
        "command": "scripts/setup-db-connection.sh"
      }
    ],
    "SubagentStop": [
      {
        "matcher": "*",
        "command": "scripts/cleanup-subagent.sh"
      }
    ]
  }
}
```

---

## 3. Agentic Coding: Claude Code как автономный агент

### 3.1. REPL-подход к разработке

Claude Code работает как **REPL (Read-Eval-Print Loop)** для разработки:

```
Цикл:
1. READ: Claude читает файлы, ошибки, результаты тестов
2. EVAL: Claude рассуждает, планирует, выбирает инструменты
3. PRINT: Claude выполняет инструменты (код, команды, запросы)
4. LOOP: Повторяет, пока задача не завершена
```

**Отличие от традиционной разработки:**

```
Традиционно:
Человек пишет код → Компилятор/интерпретатор → Ошибка →
Человек читает ошибку → Человек пишет исправление → Цикл

С Claude Code:
Claude пишет код → Компилятор/интерпретатор → Ошибка →
Claude читает ошибку → Claude анализирует → Claude пишет исправление → Цикл
```

### 3.2. Автокоррекция через обратную связь

Claude Code автоматически исправляет ошибки на основе:

**1. Lint ошибки (статический анализ)**

```
Claude Code выполняет:
→ npx eslint src/
→ Получает ошибки: "Unused variable 'temp' at line 42"
→ Автоматически исправляет: удаляет переменную
→ Повторно запускает eslint
→ ✓ Ошибок нет
```

**2. Test failures (динамические ошибки)**

```
Claude Code выполняет:
→ npm test
→ Результат: "TypeError: cannot read property 'map' of undefined"
→ Смотрит на stack trace
→ Анализирует тест и код
→ Вносит исправление (добавляет null check)
→ Повторно запускает тесты
→ ✓ Все тесты проходят
```

**3. Screenshot feedback (UI ошибки)**

```
Claude Code выполняет:
→ Запускает приложение
→ Берет screenshot UI
→ Видит: "Кнопка не видна на мобильных устройствах"
→ Анализирует CSS медиа-запросы
→ Добавляет mobile-specific стили
→ Повторно берет screenshot на разных размерах
→ ✓ Работает на всех устройствах
```

### 3.3. Режимы работы: Plan/Act и Headless

#### 3.3.1. Plan/Act режим

```
Plan (планирование):
- Claude анализирует требования
- Разбивает на подзадачи
- Определяет зависимости
- Предлагает план

Пользователь одобряет/правит план

Act (выполнение):
- Claude выполняет каждый шаг плана
- Адаптируется к ошибкам
- Достигает цели
```

**Пример:**

```
Пользователь: "Добавьте поиск с фильтрацией на главной странице"

[Plan режим]
Claude: "Вот мой план:
1. Добавить input field для поиска в компонент Header
2. Создать useSearch hook для логики фильтрации
3. Обновить компонент ItemList для показа отфильтрованных результатов
4. Добавить дебаунсинг для оптимизации
5. Написать тесты для поиска
6. Запустить e2e тесты

Готово? (y/n)"

Пользователь: "Добавьте также сортировку по релевантности"

Claude: "Обновленный план:
[план с добавлением пункта о сортировке]"

Пользователь: "Go!"

[Act режим]
Claude выполняет каждый шаг, самокорректируясь при ошибках
```

#### 3.3.2. Headless mode

Claude Code может работать без интерактивного интерфейса:

```bash
# Выполнить задачу и выйти
claude code --prompt "Add login feature" --headless

# Использовать SDK для программатического доступа
from anthropic import Anthropic

client = Anthropic()
response = client.code.execute_task(
    prompt="Fix the failing test in src/auth.test.ts",
    project_path="/path/to/project"
)
```

---

## 4. Практическая лаборатория: создание агента с хуками и субагентами

### 4.1. Сценарий: автоматизация code review процесса

Мы создадим систему, где:
1. Каждый commit автоматически проверяется хуками
2. Сложные reviews делегируются специализированному субагенту
3. Результаты отправляются в Slack
4. Все изменения логируются

### 4.2. Структура проекта

```
my-project/
├── .claude/
│   ├── agents/
│   │   ├── code-reviewer.md
│   │   └── performance-analyzer.md
│   ├── hooks.json
│   └── settings.json
├── scripts/
│   ├── pre-tool-validation.sh
│   ├── post-tool-logging.sh
│   └── slack-notifier.sh
├── src/
│   ├── app.ts
│   └── utils.ts
└── tests/
    └── app.test.ts
```

### 4.3. Конфигурация хуков

**Файл `.claude/hooks.json`:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ["Write", "Edit"],
        "command": "scripts/pre-tool-validation.sh",
        "timeout": 3000
      }
    ],
    "PostToolUse": [
      {
        "matcher": ["Write", "Edit"],
        "command": "scripts/post-tool-logging.sh",
        "timeout": 5000,
        "async": true
      },
      {
        "matcher": "Bash",
        "http": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        "timeout": 5000,
        "async": true
      }
    ],
    "SubagentStop": [
      {
        "matcher": "code-reviewer",
        "command": "scripts/review-completed-notification.sh"
      }
    ]
  }
}
```

### 4.4. Скрипт валидации перед изменением

**Файл `scripts/pre-tool-validation.sh`:**

```bash
#!/bin/bash

set -e

input=$(cat)
tool=$(echo "$input" | jq -r '.tool')
path=$(echo "$input" | jq -r '.input.path // empty')
content=$(echo "$input" | jq -r '.input.content // "extracted from file"')

echo "[$(date +'%Y-%m-%d %H:%M:%S')] PRE-VALIDATION: $tool → $path" >&2

# Проверка 1: Критические файлы
critical_files=("package.json" "tsconfig.json" ".env.production")
for file in "${critical_files[@]}"; do
  if [[ "$path" == *"$file"* ]]; then
    echo '{
      "decision": "block",
      "reason": "Critical file modification requires explicit approval",
      "file": "'"$file"'"
    }' >&2
    exit 2
  fi
done

# Проверка 2: TypeScript синтаксис
if [[ "$path" == *.ts ]] || [[ "$path" == *.tsx ]]; then
  # Проверяем, что файл содержит валидный синтаксис
  # (в реальности используйте tsc --noEmit)
  if ! echo "$content" | grep -q "^[[:space:]]*\(interface\|type\|class\|function\|const\|export\)"; then
    # Файл должен содержать хотя бы одно определение
    :  # Пропускаем для простоты
  fi
fi

# Проверка 3: Размер файла
file_size=$(echo "$content" | wc -c)
if [ "$file_size" -gt 50000 ]; then
  echo "Warning: File is large ($(($file_size / 1024))KB), consider splitting" >&2
fi

# Все проверки пройдены
exit 0
```

### 4.5. Скрипт логирования после изменения

**Файл `scripts/post-tool-logging.sh`:**

```bash
#!/bin/bash

input=$(cat)
tool=$(echo "$input" | jq -r '.tool')
path=$(echo "$input" | jq -r '.input.path // empty')
exit_code=$(echo "$input" | jq -r '.result.exitCode // 0')
timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Логирование в файл
cat >> /tmp/claude-changes.log << EOF
{
  "timestamp": "$timestamp",
  "tool": "$tool",
  "file": "$path",
  "status": "$([ $exit_code -eq 0 ] && echo 'success' || echo 'failed')",
  "exitCode": $exit_code
}
EOF

# Отправляем метрики
lines_count=$(echo "$input" | jq '.input.content // ""' | wc -l)
echo "File: $path | Lines: $lines_count | Tool: $tool | Status: $([ $exit_code -eq 0 ] && echo '✓' || echo '✗')" >> /tmp/claude-metrics.txt

exit 0
```

### 4.6. Code Reviewer субагент

**Файл `.claude/agents/code-reviewer.md`:**

```markdown
---
name: code-reviewer
description: Review code changes for quality, security, and performance
model: opus
tools:
  - Read
  - Grep
  - Bash
permissionMode: dontAsk
maxTurns: 15
memory: project
hooks:
  PostToolUse:
    - matcher: Bash
      command: scripts/lint-check.sh
---

# Code Review Expert

You are an expert code reviewer specializing in:
- **Security**: SQL injection, XSS, CSRF, authentication, encryption
- **Performance**: Algorithmic complexity, caching, database queries, memory leaks
- **Maintainability**: Code clarity, documentation, SOLID principles, DRY
- **Testing**: Coverage, edge cases, mocking strategies
- **TypeScript**: Type safety, generics, utility types

## Code Review Process

When asked to review code:

1. **Analyze the diff carefully**
   - Read the original file and the modified version
   - Understand the intent of the change
   - Check for side effects

2. **Run automated checks**
   - Use `Bash` to run linters and type checkers
   - Verify tests still pass
   - Check code coverage impact

3. **Identify issues by severity**
   - CRITICAL: Security vulnerabilities, data loss risks
   - MAJOR: Performance issues, maintainability problems
   - MINOR: Style, documentation improvements

4. **Provide constructive feedback**
   - Always mention what's working well
   - Provide code examples for suggested changes
   - Explain the reasoning behind suggestions

5. **Format your review**

```markdown
## Summary
[One sentence overview]

## Critical Issues (if any)
- Issue title
  - Location: filename:lineNumber
  - Problem: Detailed explanation
  - Impact: What could go wrong
  - Fix: Concrete code example

## Major Issues
- Issue title
  - Severity: [performance|maintainability|testability|other]
  - Current: Code snippet
  - Suggested: Better code snippet
  - Reason: Why this is better

## Minor Issues
- Issue title: Suggestion

## Strengths
- What was done well

## Verdict
APPROVED / NEEDS_CHANGES / APPROVED_WITH_SUGGESTIONS
```

## Example Review Output

If you're reviewing a database query, you might identify:
- N+1 query problem (MAJOR)
- Missing index on filtered column (PERFORMANCE)
- No connection pooling (MAJOR)
- Proper error handling (STRENGTH)

Always be constructive and remember: the goal is to improve the code, not to criticize the developer.
```

### 4.7. Performance Analyzer субагент

**Файл `.claude/agents/performance-analyzer.md`:**

```markdown
---
name: performance-analyzer
description: Analyze code performance and suggest optimizations
model: sonnet
tools:
  - Read
  - Bash
  - Grep
disallowedTools:
  - Write
  - Edit
permissionMode: dontAsk
memory: project
---

# Performance Analyzer

You are a performance optimization expert. When analyzing code:

1. **Profile the code** using available tools
   - Check algorithmic complexity
   - Identify potential bottlenecks
   - Run performance benchmarks if possible

2. **Look for common issues**
   - O(n²) or worse algorithms in critical paths
   - Unoptimized database queries (N+1 problems)
   - Unnecessary re-renders in UI code
   - Memory leaks or unbounded growth
   - Blocking operations in async code

3. **Suggest improvements**
   - Provide before/after code examples
   - Estimate the performance improvement (e.g., "10x faster")
   - Consider trade-offs (memory vs speed, complexity vs performance)

4. **Document findings**
   - Create a performance report
   - Rank optimizations by impact
   - Provide implementation guidance
```

### 4.8. Конфигурация главной сессии

**Файл `.claude/settings.json`:**

```json
{
  "permissions": {
    "default": "ask",
    "rules": [
      {
        "tools": ["Read", "Glob", "Grep"],
        "permission": "approve"
      }
    ],
    "deny": []
  },
  "tools": {
    "enabled": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
  },
  "environment": {
    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "LOG_LEVEL": "info"
  },
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "*",
        "prompt": "Log that subagent is starting",
        "async": true
      }
    ]
  }
}
```

### 4.9. Полный пример использования: code review workflow

**Пользователь просит:**
```
"Добавьте функцию поиска в базе данных и пусть код-ревьюер
проверит изменения на качество и производительность"
```

**Что происходит за кулисами:**

```
1. MAIN AGENT READ:
   Claude читает текущую структуру базы данных
   Claude читает существующие поиск-функции

2. MAIN AGENT PLAN:
   "Я добавлю функцию поиска с:
    - индексированием по text полям
    - limit и offset для пагинации
    - кэшированием частых запросов"

3. MAIN AGENT EXECUTE:
   - Создает новый файл src/search.ts
   [Pre-tool validation проверяет: ✓ Не критический файл]
   - Модифицирует src/db/index.ts для регистрации функции
   [Post-tool logging: ✓ Файл создан, logging отправлен]

4. RUN TESTS:
   - npx jest src/search.test.ts
   [Post-tool logging отправляет результаты в Slack]

5. DELEGATE TO CODE-REVIEWER:
   Task("Review the new search function in src/search.ts
        for quality and security issues")

   ↓
   Code-reviewer subagent:
   - Читает src/search.ts
   - Запускает linter
   - Проверяет на SQL injection
   - Возвращает review:
     "NEEDS_CHANGES:
      - Missing null check on searchTerm (CRITICAL)
      - N+1 query problem on joins (MAJOR)
      - No rate limiting (MAJOR)
      - Good error handling (STRENGTH)"

6. MAIN AGENT FIXES:
   Claude читает review
   Исправляет указанные проблемы:
   - Добавляет null check
   - Оптимизирует JOIN запрос
   - Добавляет rate limiting middleware

7. RE-REVIEW:
   Запускает code-reviewer субагента снова
   Получает: "APPROVED_WITH_SUGGESTIONS"

8. FINAL STEPS:
   - npm test (все тесты проходят)
   - git commit (автоматический коммит)
   - Отправляет итоговый отчет в Slack

Время выполнения: 5 минут вместо 30 минут (если делать вручную)
```

### 4.10. Мониторинг и логирование хуков

**Проверка логов хуков:**

```bash
# Просмотр всех изменений файлов
tail -100 /tmp/claude-changes.log | jq '.file, .status'

# Анализ метрик
grep "Status: ✓" /tmp/claude-metrics.txt | wc -l  # Успешных операций

# Поиск ошибок
grep "Status: ✗" /tmp/claude-metrics.txt  # Неудачных операций
```

**Структура лога:**

```json
{
  "timestamp": "2026-03-10T15:45:23Z",
  "tool": "Write",
  "file": "src/search.ts",
  "status": "success",
  "exitCode": 0
}
{
  "timestamp": "2026-03-10T15:45:24Z",
  "tool": "Bash",
  "file": "N/A (command execution)",
  "status": "success",
  "exitCode": 0
}
```

---

## 5. Интеграция: хуки + субагенты = мощная система

### 5.1. Как они работают вместе

```
Главная сессия (Main Agent):
├─ Использует PreToolUse хук для валидации всех команд
├─ Логирует все действия через PostToolUse хук
└─ Делегирует сложные задачи субагентам через Task tool

Субагент 1 (Code Reviewer):
├─ Имеет свои собственные хуки (локальные)
├─ Читает файлы для анализа
└─ Возвращает результаты в главный агент

Субагент 2 (Performance Analyzer):
├─ Запускает benchmark тесты через Bash
├─ Логирует результаты через свои хуки
└─ Возвращает оптимизации в главный агент

Главный агент интегрирует результаты и принимает решения
```

### 5.2. Best Practices

**1. Используйте хуки для контроля, субагентов для масштабирования**

```
Плохо:
- Один большой хук, который делает всё
- Один большой агент, который все обрабатывает

Хорошо:
- Маленькие специализированные хуки (валидация, логирование)
- Специализированные субагенты для сложных задач
- Главный агент оркестрирует всё
```

**2. Изолируйте контекст с помощью SubagentStart хука**

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "database-agent",
        "command": "scripts/setup-db-credentials.sh"
      }
    ]
  }
}
```

**3. Используйте worktree isolation для параллельной разработки**

```yaml
---
name: feature-worker
isolation: worktree
---
```

**4. Persistent memory для долгоживущих знаний**

```yaml
---
name: architectural-advisor
memory: project
---
```

---

## Итоги

В этом подмодуле мы изучили:

1. **Хуки** — мощный механизм для перехвата и контроля событий агентного цикла
   - 13+ типов событий
   - 3 типа обработчиков (command, HTTP, prompt)
   - Exit codes для контроля поведения

2. **Субагенты** — система для параллелизации и изоляции контекста
   - 3 встроенных специализированных агента
   - Создание пользовательских субагентов
   - Паттерны: fan-out/fan-in, pipeline, specialist delegation

3. **Интеграция** — хуки и субагенты работают вместе
   - Локальные и глобальные хуки для субагентов
   - Worktree isolation для параллельной разработки
   - Persistent memory для накопления знаний

4. **Практика** — полный пример code review workflow
   - Валидация входных данных
   - Логирование и мониторинг
   - Делегирование сложных задач специалистам

Это создает полнофункциональную систему, где Claude Code может работать не как простой код-ассистент, а как настоящий агент разработки, способный планировать, выполнять, контролировать и улучшать свои действия.
