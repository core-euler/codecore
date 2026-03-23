---
module: "08_devops"
lesson: 2
title: "Мониторинг, деплой и инфраструктура"
type: "practice"
prerequisites: ["08_devops/lesson_01"]
difficulty: "intermediate"
tags: ["monitoring", "deploy", "docker", "cost-tracking"]
---

# Модуль 6.2: Мониторинг, деплой и инфраструктура для агентов

## Введение

LLM-агенты, работающие в production-среде, требуют сложной инфраструктуры мониторинга и управления. Когда ваш агент потребляет токены Claude, делает запросы к API, взаимодействует с базами данных и обрабатывает пользовательские данные — вы должны знать, что происходит на каждом этапе.

В этом разделе мы рассмотрим полный цикл мониторинга, spec-driven разработки и современные стеки развертывания.

---

## 1. Мониторинг использования LLM-агентов

### 1.1 Зачем нужен мониторинг токенов

При работе с LLM-агентами в production самый критичный метрик — это **использование токенов**, которое напрямую влияет на стоимость. Без контроля можно быстро оказаться в ситуации, когда:

- Агент попадает в бесконечный цикл и расходует тысячи токенов
- Один пользователь случайно загружает 200MB контекста
- Промпт был неоптимизирован и каждый запрос тратит в 5 раз больше токенов

**Ключевые метрики для отслеживания:**

| Метрика | Назначение | Тревога |
|---------|-----------|--------|
| Входные токены | Размер контекста и промпта | > 50K на запрос |
| Выходные токены | Размер ответа модели | > 10K на ответ |
| Стоимость за запрос | Финансовый импакт | > $1 за запрос |
| Стоимость за день | Daily budget tracking | > $100/день |
| Burn rate | Токены в минуту | Растет необъяснимо |

### 1.2 Архитектура мониторинга

Типичная система мониторинга состоит из:

**Data Layer** — сбор логов из всех источников. Каждый вызов API логируется с метаданными: timestamp, user, model, token counts, cost.

**Storage** — логи хранятся в структурированной БД (PostgreSQL, BigQuery) с индексами для быстрого поиска по user, date, model.

**Analysis Engine** — вычисляет метрики: дневная стоимость, средний использование, тренды, anomalies. Использует SQL запросы и ML для обнаружения необычной активности.

**Alerting** — система алертов на разных уровнях критичности. Если дневной spend превышает budget на 20%, отправляется email. Если превышает на 50% — SMS и отключение агента.

**Dashboard** — визуализация в Grafana или DataDog, где видны графики использования в real-time, прогнозы на месяц, history по дням.

### 1.3 Сессионная модель Claude Code

Важное понятие — **5-часовые rolling окна** для лимитов токенов. Это означает:

- Каждая новая сессия Claude Code получает "свеженные" лимиты токенов
- Но это rolling окно: если вы начали сессию в 10:30 AM, она активна до 3:30 PM
- Во время этого окна все токены считаются против лимита
- После 3:30 PM лимит сбрасывается, и новая сессия может быть начата

**Практическое значение:** если у вас есть Max20 план с 220K токенов, это лимит за 5-часовой период, а не за день.

### 1.4 Что отслеживать для агентов

**Per-session metrics:**
- Токены на сессию (input + output + cache creation)
- Среднее время между сообщениями
- Quantity и complexity of tool calls
- Success rate (какой процент запросов завершился успешно)

**Per-user metrics:**
- Дневный бюджет потребления
- Frequency использования агента
- Types задач, которые они запускают
- Cost per completed task

**Quality metrics:**
- Accuracy выхода агента (проверяется через smoke tests)
- Latency (сколько времени занял запрос)
- Error rate (процент failed запросов)

### 1.5 Настройка мониторинга

Базовая конфигурация мониторинга хранится в `observability.yml`:

```yaml
# observability.yml
monitoring:
  log_level: INFO
  token_tracking: enabled
  alert_thresholds:
    daily_budget_usd: 100
    warn_at_percentage: 75      # Предупреждение при 75% использовании
    critical_at_percentage: 90
    hard_limit: 110             # Отключить при 110% бюджета

  metrics_to_track:
    - input_tokens
    - output_tokens
    - cache_read_tokens
    - cache_creation_tokens
    - total_cost
    - request_latency
    - model_used
    - tool_calls_count

  retention:
    logs: 90 days               # Храним логи 3 месяца
    metrics: 1 year             # Метрики - год

  dashboard:
    refresh_rate: 5 seconds
    widgets:
      - daily_spend
      - hour_by_hour_trends
      - top_users_by_cost
      - error_rate
```

---

## 2. Spec-Driven Development с AI

### 2.1 Что такое Spec-Driven Development

**Spec-Driven Development (SDD)** — это парадигма разработки, где полная спецификация **предшествует** разработке, а не следует за ней.

Традиционный процесс:
- Идея → Код → Тестирование → Надежда на лучшее

Spec-Driven процесс:
- Идея → **Полная спецификация** → Валидация спеки → Код (из спеки) → Тестирование (согласно спеке)

**Ключевое преимущество для AI:** когда ваш агент имеет четкую, структурированную спецификацию, он может ее беспрепятственно следовать. Спецификация становится не просто документацией, а **исполняемым контрактом**.

### 2.2 Процесс SDD: От идеи к реализации

**Шаг 1: Constitution (Конституция проекта)**

Определяем принципы и ограничения проекта. Это документ, который агент консультирует для каждого решения:
- Code quality standards (тип systems, код coverage, документация)
- Performance требования (latency, throughput)
- Architecture паттерны (как организовать код)
- Security требования (что защищать)

Пример constitution для задачного приложения:
- Всегда используем TypeScript с strict mode
- Минимум 80% code coverage для критических путей
- Database queries должны быть < 100ms
- Все компоненты имеют JSDoc документацию

**Шаг 2: Specification (Спецификация)**

Описываем полностью, что должна делать система:
- User stories (как пользователь будет взаимодействовать)
- Functional requirements (что именно делает система)
- Acceptance criteria (как мы узнаем, что это работает)
- Data models (какие сущности, как они связаны)

Пример спецификации для photo album app:
- Пользователь может создавать альбомы, которые группируются по датам
- Альбомы можно переупорядочивать drag-and-drop
- Фотографии в альбоме показываются в grid'е с zoom'ом
- Удаление альбома требует подтверждения
- Фото хранятся локально (не на сервере)

**Шаг 3: Implementation Plan (План реализации)**

Выбираем технологический стек и архитектуру:
- Frontend: React 18, TypeScript, TailwindCSS
- Backend: Next.js Server Actions
- Database: SQLite с Drizzle ORM
- Build: Vite, pnpm

Описываем архитектуру: какие компоненты, как они взаимодействуют.

**Шаг 4: Task Breakdown (Разбиение на задачи)**

Спецификация и план парсятся в детализированный список задач:
- Phase 1: Project Setup (инициализация, конфигурация)
- Phase 2: Core Components (React компоненты)
- Phase 3: State Management (Redux, управление состоянием)
- Phase 4: Database (создание schema, миграции)
- Phase 5: Integration (связывание всех частей)

Каждая задача:
- Имеет четкое описание
- Зависит от других (task3 требует completion task1 и task2)
- Помечена как sequential или parallel

**Шаг 5: Implementation (Реализация)**

Агент берет task list и выполняет автоматически:
- Для каждой задачи читает спецификацию и constitution
- Реализует, следуя стандартам
- Запускает tests для проверки
- Переходит к следующей задаче

### 2.3 Инструменты для SDD

**GitHub Spec Kit** — это фреймворк от GitHub для управления SDD. Он предоставляет:
- Структурированные команды для создания constitution, spec, plan, tasks
- Парсинг спецификации в исполняемые инструкции
- Integration с popular AI agents (Claude Code, Gemini, Copilot, Cursor)

Команды:
```bash
specify init project --ai claude          # Инициализация
/speckit.constitution                    # Создание constitution
/speckit.specify "описание проекта"      # Создание спецификации
/speckit.plan "технологический стек"    # План реализации
/speckit.tasks                           # Генерация task list
/speckit.implement                       # Автоматическая реализация
```

---

## 3. Deployment-стеки для AI-приложений

### 3.1 Cloudflare + Next.js: Edge-first архитектура

**Cloudflare** предоставляет глобальную инфраструктуру с присутствием в 300+ городов мира. Это идеально для LLM-приложений:

- **Workers**: serverless функции на edge (ближе к пользователю = меньше задержка)
- **D1**: SQLite база на edge (распределенная, низкая latency)
- **R2**: S3-совместимое хранилище для больших файлов
- **Pages**: хостинг статических сайтов
- **Workers AI**: inference для моделей прямо на edge

**Архитектура приложения на Cloudflare:**

```
User запрос
    ↓
Cloudflare Edge (ближайшая локация к пользователю)
    ├─ Cache Layer (если response кэширован, instant)
    ├─ WAF (защита от атак)
    └─ Workers (ваше приложение)
        ├─ Next.js Server Components
        ├─ Server Actions (API логика)
        ├─ AI inference (через Workers AI)
        └─ Database (D1)
```

**Преимущества:**
- Latency: ответ приходит из ближайшей точки (обычно < 100ms)
- Масштабируемость: Cloudflare масштабирует автоматически
- Cost: бесплатный tier для малых приложений, затем pay-as-you-go
- Security: встроенный WAF и DDoS protection

**Организация проекта:**

Типичная структура Next.js на Cloudflare:

```
src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Группа маршрутов для авторизации
│   ├── dashboard/         # Защищенные страницы
│   ├── api/               # API endpoints
│   │   ├── summarize/     # AI endpoints
│   │   ├── tasks/         # CRUD
│   │   └── auth/          # Auth logic
│   └── globals.css
│
├── modules/               # Feature модули (auth, tasks, ai)
├── db/                    # Database (schema, queries)
├── services/              # Business logic слой
├── components/            # Shared React компоненты
├── lib/                   # Utilities
└── drizzle/              # Database migrations
```

### 3.2 Database-first стратегия с D1

D1 — это SQLite база на Cloudflare. Преимущества:
- Нет необходимости в отдельном database сервере
- Реплицируется автоматически на edge
- ACID гарантии
- Совместима с Drizzle ORM

**Процесс создания D1 базы:**

1. Определяете schema в Drizzle (типобезопасный способ писать SQL)
2. Генерируете миграцию
3. Применяете миграцию к локальной и remote базе

**Структура database schema:**

Для приложения задач:

```
users table:
  id (primary key)
  email (unique)
  name
  created_at

tasks table:
  id (primary key)
  user_id (foreign key → users)
  title
  description
  completed (boolean)
  priority (0-10)
  due_date
  created_at
  updated_at
```

**Миграции:** каждое изменение schema (добавление колонны, создание таблицы) записывается в файл миграции и версионируется в Git. Это позволяет:
- Отслеживать историю изменений БД
- Откатываться к предыдущей версии при необходимости
- Одновременно иметь разные версии в dev и production

### 3.3 Server Actions: API без создания API

Next.js Server Actions позволяют писать backend логику прямо в компонентах, без необходимости создавать отдельные API routes.

Вместо традиционного:
- Frontend отправляет HTTP запрос на `/api/tasks/create`
- Backend обрабатывает, сохраняет в БД, возвращает результат

Используете Server Action:
- Компонент определяет функцию, помеченную `"use server"`
- Функция может работать с БД напрямую
- Frontend вызывает функцию как обычную функцию

**Преимущества:**
- Типобезопасность: компилятор проверяет типы между frontend и backend
- Нет необходимости писать API контракт (OpenAPI, etc.)
- Более простой code flow

### 3.4 Основные сервисы для LLM-приложений

| Сервис | Назначение | Пример использования |
|--------|-----------|----------------------|
| **Workers** | Backend логика | Обработка requests, вызовы AI |
| **D1** | Persistence | Сохранение tasks, users, history |
| **R2** | File storage | Сохранение uploaded документов, images |
| **Workers AI** | AI inference | Встроенные модели для classification |
| **Durable Objects** | Stateful compute | Sessions, rate limiting, caching |
| **KV** | Key-value store | Кэширование, сессии, rate limits |
| **Analytics Engine** | Метрики | Отслеживание usage, costs, performance |

---

## 4. Observability для LLM-агентов

### 4.1 Трехуровневая система observability

**Logging** (детальные логи):
- Каждый запрос логируется с полными параметрами
- Включает timestamp, user_id, model, tokens, cost
- Хранится в долгосроке для отладки и аудита
- Но без чувствительных данных (passwords, API keys)

**Metrics** (агрегированные числа):
- Daily spend, hourly token consumption
- Request latency, error rates, success rates
- Вычисляются из логов каждый час
- Использются для alerting и dashboards

**Traces** (сквозное отслеживание):
- Когда request входит, система создает trace ID
- Следит за этим request через все системы (AI, DB, cache)
- Показывает, где request потерял время
- Полезна для поиска bottleneck'ов

### 4.2 Что логировать

**Требуется логировать:**
- Timestamp, request ID, user ID
- Model name, parameters (temperature, max_tokens)
- Input token count, output token count
- Стоимость в USD
- Latency (time to first token, total time)
- Success/error status
- Tool calls (не полные аргументы, только имена)

**НЕ логировать:**
- Полные промпты (особенно системные)
- Полные ответы модели
- API ключи, passwords, credentials
- Конфиденциальные данные пользователя

### 4.3 Alerting стратегия

Три уровня alerts:

**Level 1: Info** (50% использования бюджета)
- Просто информируем пользователя
- "Вы использовали 50% дневного бюджета"

**Level 2: Warning** (75% использования)
- Email алерт
- "Осталось 25% вашего бюджета на сегодня. Текущий burn rate: $1.5/мин"

**Level 3: Critical** (90% использования)
- Email + SMS
- Начинаем rate limiting (замедляем запросы)
- "CRITICAL: Осталось 10% бюджета. Новые запросы будут замедлены"

**Level 4: Hard Limit** (110% использования)
- Отключаем агента
- Требуется manual intervention для перезагрузки

---

## 5. Cost Control и Rate Limiting

### 5.1 Стратегии контроля стоимости

**Per-request limits:**
- Максимум input tokens = 50K (если больше, отклоняем)
- Максимум output tokens = 5K per request
- Максимум cost = $1 per single request

**Per-user limits:**
- Дневный бюджет: $10/день
- Ежемесячный лимит: $300/месяц
- Если превышен, требуется подтверждение от администратора

**Per-model limits:**
- Используем более дешевую модель для simple tasks
- Используем более мощную для complex tasks
- Автоматическое routing по сложности

### 5.2 Impl эmentation: Token Budget

Система работает так:

1. **Начало дня**: каждому пользователю дается $10 бюджета
2. **Каждый запрос**: вычисляем estimated стоимость перед отправкой
3. **Если < budget**: отправляем запрос, вычитаем стоимость из бюджета
4. **Если >= budget**: отклоняем, предлагаем upgrade
5. **Конец дня**: неиспользованный бюджет не переносится на следующий день

---

## Резюме

Production LLM-приложение требует:

- **Мониторинга** — real-time tracking токенов и стоимости
- **Spec-Driven Development** — четкие спецификации перед разработкой
- **Modern stacks** — Cloudflare, Next.js, D1 для низкой latency
- **Observability** — логи, метрики, traces для отладки
- **Cost controls** — четкие лимиты и budget tracking

Без этого инфраструктуры production deployment быстро становится хаосом с непредсказуемыми расходами и недиагностируемыми проблемами.
