# CodeCore
## Терминальный AI-агент — Техническое задание и Roadmap
`v1.0 · 2026 · @CoreEuler`

---

## 1. Концепция

CodeCore — персональный терминальный AI-агент для разработки, независимый от конкретных провайдеров и инструментов. Создаётся как живой инструмент: запускается с минимальной рабочей версией и наращивается итеративно.

> **Главная идея:** не зависеть от блокировок и white-list политик. Один инструмент, множество провайдеров. Переключение — одна строка конфига.

### 1.1 Ключевые принципы

- **Провайдер-агностичность** — единый интерфейс, любой OpenAI-compatible backend
- **Метрики первого класса** — каждый запрос логируется, накапливается статистика
- **Skill-система** — динамическая подгрузка контекста под тип задачи
- **Итеративный рост** — v0.1 уже работает, каждая версия добавляет конкретную фичу
- **Собственная база знаний** — со временем агент знает твои паттерны лучше любого стороннего инструмента

### 1.2 Позиционирование

|  | CodeCore | Aider / Claude Code |
|---|---|---|
| Провайдер | Любой, с fallback | Привязан к конкретному |
| Метрики | Встроены, SQLite | Нет / внешние |
| Skill-система | Нативная, под твои задачи | Ограниченная |
| Контроль pipeline | Полный | Фиксированный |
| Доступность из РФ | Конфигурируется | Зависит от инструмента |

---

## 2. Технический стек

### 2.1 Ядро

| Библиотека | Роль | Почему |
|---|---|---|
| `litellm` | Абстракция провайдеров | 100+ провайдеров, один интерфейс |
| `rich` | Терминальный UI | Цвет, таблицы, прогресс без GUI |
| `prompt_toolkit` | REPL с историей | Autocomplete, keybindings, history |
| `pydantic` | Конфиг и модели данных | Валидация, типизация, ясность |
| `sqlite3` | База метрик | Встроен в Python, не требует сервера |
| `PyYAML` | Конфигурация | Читаемый формат реестра провайдеров |
| `httpx` | Ping провайдеров | Async, быстрый health-check |

### 2.2 Структура проекта

```
codecore/
├── main.py                  # точка входа, REPL-цикл
├── config.yaml              # пользовательские настройки
├── providers/
│   ├── router.py            # выбор провайдера, fallback-логика
│   ├── health.py            # ping + проверка доступности
│   └── registry.yaml        # реестр всех провайдеров и моделей
├── context/
│   ├── manager.py           # управление файлами в контексте
│   └── skills/              # skill-файлы (.md)
│       ├── backend.md
│       ├── review.md
│       └── jung.md
├── metrics/
│   ├── tracker.py           # запись метрик после каждого запроса
│   └── db.sqlite            # история сессий
├── memory/
│   └── model_perf.json      # накопленная статистика по моделям
└── utils/
    ├── diff.py              # применение изменений к файлам
    └── display.py           # rich-компоненты
```

---

## 3. Провайдеры и модели

### 3.1 Реестр провайдеров (registry.yaml)

```yaml
providers:
  - name: deepseek
    base_url: https://api.deepseek.com
    env_key: DEEPSEEK_API_KEY
    models:
      - id: deepseek-chat
        alias: ds-v3
        strengths: [code, refactor, general]
        cost_per_1k_in: 0.00014
        cost_per_1k_out: 0.00028
      - id: deepseek-reasoner
        alias: ds-r1
        strengths: [architecture, planning, debug]
        cost_per_1k_in: 0.00055
        cost_per_1k_out: 0.00219
    vpn_required: false
    priority: 1

  - name: mistral
    base_url: https://api.mistral.ai
    env_key: MISTRAL_API_KEY
    models:
      - id: codestral-latest
        alias: codestral
        strengths: [code, completion, fast]
    vpn_required: false
    priority: 2

  - name: openrouter
    base_url: https://openrouter.ai/api/v1
    env_key: OPENROUTER_API_KEY
    models:
      - id: anthropic/claude-sonnet-4-5
        alias: claude
        strengths: [complex, creative, analysis]
    vpn_required: true
    priority: 3

  - name: yandex
    base_url: https://llm.api.cloud.yandex.net
    env_key: YANDEX_API_KEY
    models:
      - id: yandexgpt
        alias: ygpt
        strengths: [russian, general]
    vpn_required: false
    priority: 99
```

### 3.2 Логика роутера

1. При запуске — async ping всех провайдеров (таймаут 2 сек)
2. Фильтрация: исключаются `vpn_required: true` если VPN недоступен
3. Сортировка по `priority`, выбирается лучший доступный
4. При ошибке во время сессии — автоматический fallback на следующего
5. Результат пинга кэшируется на 5 минут

---

## 4. REPL — команды и интерфейс

### 4.1 Команды

| Команда | Описание |
|---|---|
| `/add <файл>` | Добавить файл(ы) в контекст текущей сессии |
| `/drop <файл>` | Убрать файл из контекста |
| `/skill <n>` | Загрузить skill-файл в системный промпт |
| `/model <alias>` | Переключить модель прямо в сессии |
| `/status` | Провайдеры, модель, контекст, токены сессии |
| `/stats [N]` | Статистика последних N сессий + лучшие модели по задачам |
| `/run <cmd>` | Выполнить bash-команду, вывод скормить модели |
| `/tag <тип>` | Тегировать текущую задачу (refactor, debug, arch, etc.) |
| `/rate <1-5>` | Оценить качество последнего ответа |
| `/undo` | Откатить последнее изменение файла (git reset) |
| `/clear` | Очистить контекст сессии |
| `/ping` | Перепроверить доступность провайдеров |
| `/help` | Список команд |
| `/exit` | Завершить сессию, записать итог в метрики |

### 4.2 Строка состояния

```
[codecore] DeepSeek V3 (ds-v3)  ·  no VPN  ·  ctx: 2 files, 3.2k tokens  ·  session: $0.0012
> _
```

---

## 5. Метрики и аналитика

### 5.1 Схема базы данных

```sql
-- sessions
CREATE TABLE sessions (
  id          TEXT PRIMARY KEY,  -- UUID
  started_at  TEXT,
  ended_at    TEXT,
  task_tag    TEXT,              -- refactor | debug | arch | general
  provider    TEXT,
  model       TEXT,
  skill       TEXT
);

-- requests (один запрос = одна строка)
CREATE TABLE requests (
  id            TEXT PRIMARY KEY,
  session_id    TEXT REFERENCES sessions(id),
  timestamp     TEXT,
  model         TEXT,
  provider      TEXT,
  input_tokens  INTEGER,
  output_tokens INTEGER,
  latency_ms    INTEGER,
  cost_usd      REAL,
  rating        INTEGER          -- NULL до оценки пользователем
);
```

### 5.2 Вывод /stats

```
[codecore] Статистика за последние 30 дней

По моделям (avg rating / cost per request):
  deepseek-chat      ████████  4.3★  $0.0009  [refactor, general]
  codestral-latest   ███████   4.1★  $0.0006  [code, fast]
  deepseek-reasoner  ██████    4.0★  $0.0031  [arch, debug]

Лучшая модель для 'refactor' → deepseek-chat (4.3★, n=18)
Лучшая модель для 'arch'     → deepseek-reasoner (4.2★, n=7)

Общий расход: $0.84  |  Запросов: 94  |  Токенов: 1.2M
```

### 5.3 Model Performance Memory

После каждой оценённой сессии агент обновляет `model_perf.json`. При следующем запуске с тегом задачи — предлагает оптимальную модель:

```
[codecore] Для задач типа 'refactor' рекомендуется deepseek-chat (avg 4.3★, $0.0009/req)
           Использовать? [Y/n]: _
```

---

## 6. Skill-система

### 6.1 Формат skill-файла

```markdown
# skills/backend.md
---
name: backend
description: FastAPI / Python / async backend разработка
tags: [python, fastapi, async, postgresql]
---

## Контекст
Ты работаешь с Python backend на FastAPI.
Всегда используй async/await, pydantic v2, SQLAlchemy 2.0.

## Правила
- Разбивай на слои: router → service → repository
- Никогда не пиши бизнес-логику в роутерах
- Все ошибки через HTTPException с понятным detail

## Стиль кода
- Type hints везде
- Docstrings на публичных функциях
- Prefer dependency injection через Depends()
```

### 6.2 Встроенные скиллы (v0.1)

- `backend.md` — FastAPI, async Python, сервисный слой
- `review.md` — код-ревью, поиск проблем, предложения
- `arch.md` — проектирование систем, ADR-документы
- `telegram.md` — Telegram боты, aiogram, webhook-архитектура
- `jung.md` — для JungCore задач, психоаналитический контекст

---

## 7. Roadmap

> Каждая версия — рабочий инструмент. Не переходи к следующей, пока текущая не используется в реальных задачах.

### v0.1 — Рабочее ядро

**Цель:** минимальный агент, который уже заменяет ручные запросы к API.

| Задача | Детали |
|---|---|
| REPL-цикл (prompt → response → loop) | prompt_toolkit, история команд |
| Провайдер-роутер с ping | litellm + httpx health-check |
| registry.yaml — DeepSeek + Mistral + OpenRouter | vpn_required флаг |
| Базовые команды: /add /model /status /exit | Минимальный рабочий набор |
| Метрики: токены + стоимость + latency в SQLite | Автозапись после каждого запроса |
| rich UI: цветной вывод, строка состояния | Приятно работать с первого дня |

---

### v0.2 — Контекст и скиллы

**Цель:** агент знает структуру проекта и умеет переключать режим работы.

| Задача | Детали |
|---|---|
| Skill-система: /skill, динамический инджект | Читает skills/*.md в системный промпт |
| Context manager: /add /drop файлов | Показывает токены на файл |
| Repo-map lite: автоматический обзор структуры проекта | find + tree, краткий summary |
| Теги задач /tag, оценка /rate | Запись в БД для будущей аналитики |
| .codecore конфиг на уровне проекта | Дефолтные скиллы и модель под проект |

---

### v0.3 — Аналитика и память

**Цель:** агент начинает учиться на твоих паттернах.

| Задача | Детали |
|---|---|
| Model Performance Memory | model_perf.json, рекомендации при запуске |
| /stats — таблица лучших моделей по тегам задач | SQL aggregation, rich-таблица |
| Автоматический выбор модели по тегу задачи | Если avg_rating > порога — предлагает |
| Сравнительный режим: один промпт → N моделей | Для бенчмарков твоих задач |
| Экспорт метрик в CSV/JSON | Для анализа во внешних инструментах |

---

### v0.4 — Итерация и автоматизация

**Цель:** агент закрывает задачи полностью, не только отвечает.

| Задача | Детали |
|---|---|
| /run: выполнение команд + инджект вывода | bash, pytest, linter — результат в контекст |
| Diff-применение: агент пишет изменения в файлы | Формат search/replace блоков |
| /undo через git: откат последнего изменения | git diff перед применением |
| Error-loop: ошибка → автоматически скармливается модели | Итерирует до fix или N попыток |
| Watch-режим: следит за файлами, реагирует на изменения | Для TDD-паттерна |

---

### v0.5 — Мультиагентность

**Цель:** сложные задачи решаются цепочкой агентов.

| Задача | Детали |
|---|---|
| Planner + Coder режим (--architect) | Первая модель планирует, вторая реализует |
| Reviewer агент: автоматический ревью после изменений | Третья модель проверяет результат |
| Pipeline конфигурация в YAML | Цепочки агентов под типы задач |
| Интеграция с Core-продуктами (LeadCore, JungCore) | Специфические pipeline под каждый проект |

---

### v1.0 — Зрелый инструмент

**Цель:** CodeCore превосходит Aider в твоих конкретных задачах по метрикам.

| Задача | Детали |
|---|---|
| Персональный бенчмарк: CodeCore vs Aider vs Claude Code | На реальных задачах, с твоими метриками |
| DSL-датасет: логи взаимодействий для анализа паттернов | Фундамент будущей DSL-системы |
| Plugin-система: сторонние расширения | Открытая архитектура |
| Опенсорс или DevCore showcase | Публикация как доказательство экспертизы |

---

## 8. Запуск v0.1

### Установка

```bash
git clone https://github.com/CoreEuler/codecore
cd codecore
python -m venv .venv && source .venv/bin/activate
pip install litellm rich prompt_toolkit pydantic pyyaml httpx
```

### Конфигурация

```bash
# .env
DEEPSEEK_API_KEY=sk-...
MISTRAL_API_KEY=...
OPENROUTER_API_KEY=sk-or-...
```

### Запуск

```bash
# Базовый — авто-выбор лучшего доступного провайдера
python -m codecore

# С указанием модели
python -m codecore --model ds-r1

# С предзагруженным скиллом и файлами
python -m codecore --skill backend src/bot.py utils/db.py

# Алиас (добавить в .zshrc)
alias cc='cd ~/projects/codecore && python -m codecore'
```

---

## 9. Критерии готовности версий

| Версия | Критерий |
|---|---|
| v0.1 | Использую CodeCore в реальной задаче вместо прямого API-запроса |
| v0.2 | Переключаю скиллы между разными Core-проектами без переконфигурации |
| v0.3 | Смотрю на /stats и принимаю решение о выборе модели на основе данных |
| v0.4 | CodeCore закрывает задачу от промпта до закоммиченного кода |
| v0.5 | Запускаю мультиагентный pipeline на нетривиальной фиче |
| v1.0 | CodeCore показывает лучшие метрики на моих задачах чем Aider |

---

*CodeCore · @CoreEuler · 2026*
