---
module: "09_models"
lesson: 0
title: "Модели и Runtime — полная глава"
type: "reference"
prerequisites: []
difficulty: "beginner"
tags: ["models", "claude", "openai", "runtime", "llama"]
---

# Модуль 7: Модели и Runtime

## Введение

В 2025-2026 годах разработчики сталкиваются с беспрецедентным выбором языковых моделей и сред их выполнения. Выбор правильной комбинации модели, платформы доставки и интегрированной среды разработки стал критической задачей для построения эффективных AI-агентов.

Этот модуль охватывает полный спектр доступных решений и учит принимать обоснованные решения о выборе инструментов.

---

## 1. Ландшафт современных LLM (2025-2026)

### 1.1 Главные игроки

#### Claude (Anthropic)

Семейство Claude предлагает три модели с разными точками оптимизации:

| Модель | Context | Лучше всего для |
|--------|---------|-----------------|
| Claude Opus 4.6 | 200K | Сложные рассуждения, архитектура, анализ |
| Claude Sonnet 4.5 | 200K | Production, balance quality/speed, обучение |
| Claude Haiku 4.5 | 200K | Быстрые задачи, streaming, масштабирование |

**Когда использовать:** Claude лучший выбор для:
- Сложных инженерных задач (требуют глубокого анализа)
- Production систем (reliability и safety)
- Работы с большим контекстом (200K токенов достаточно для целых книг)

**Цена и производительность:**
- Opus: самый дорогой, но лучшее качество (рассуждение, анализ)
- Sonnet: 2x быстрее Opus с минимальной потерей качества
- Haiku: 5x быстрее Sonnet, для simple tasks

#### GPT-4o (OpenAI)

OpenAI предлагает сильные multimodal модели (текст, изображения, видео, аудио).

**Когда использовать:**
- Работа с изображениями (vision capabilities)
- Мультимодальные приложения
- Когда нужна ecosystem (DALL-E, Whisper, TTS)

#### Gemini (Google)

Google's семейство моделей с фокусом на multimodal и context length.

**Когда использовать:**
- Очень большой контекст (1M+ токенов)
- Бюджетные приложения (Gemini Flash очень дешев)
- Integration с Google сервисами

#### Специализированные модели

**Для кодирования:**
- DeepSeek Coder: открытая, высокое качество кодирования
- Mistral Code: специализирована для code completion
- Kimi K2: MoE архитектура, хороша для агентов

**Для reasoning:**
- o1 (OpenAI): специально обучена долгому reasoning
- DeepSeek-R1: открытая альтернатива o1

### 1.2 Критерии выбора модели

При выборе модели учитывайте:

**Качество:**
- MMLU score: общее знание (выше = лучше)
- LiveCodeBench: способность писать рабочий код
- SWE-bench: решение реальных issues (для агентов)
- Math reasoning: способность к математическим рассуждениям

**Скорость:**
- TTFT (Time To First Token): задержка до первого токена (100-500ms для облака)
- TPS (Tokens Per Second): сколько токенов генерируется в секунду (30-100 для облака)
- Стоимость: input tokens дешевле, output токены дороже

**Context window:**
- Сколько токенов может вместить в контекст
- 200K достаточно для большинства задач
- 1M+ нужна для анализа больших кодовых баз или эмпирических датасетов

**API совместимость:**
- OpenAI-совместимый API (standard де-факто)
- Anthropic API (для Claude)
- Proprietary API (для Google Gemini)

### 1.3 Матрица выбора: когда какую модель использовать

```
                  Quality-focused      Cost-focused      Speed-focused
Simple Task      Haiku/Gemini Flash   Haiku/Mistral     Haiku/Flash
Medium Task      Sonnet               Mistral 7B        Sonnet
Complex Task     Opus/o1              DeepSeek Coder    Sonnet
Coding           DeepSeek Coder       Mistral Code      Haiku
Multimodal       GPT-4o               Gemini Flash      GPT-4 Vision
Reasoning        o1/DeepSeek-R1       (не рекомендуется)  (не рекомендуется)
```

---

## 2. Cloud vs Local:决策фреймворк

### 2.1 Cloud API (Claude, GPT-4, Gemini)

**Преимущества:**
- Никаких setup — просто API ключ и готово
- Лучшие модели доступны сразу
- Масштабируемость — не беспокоишься об инфраструктуре
- Автоматические updates — модели улучшаются без вашего участия
- Monioring и logging встроены

**Недостатки:**
- Стоимость может быть высокой для больших объемов
- Данные отправляются в облако (privacy concerns для некоторых)
- Network latency (обычно 200-500ms)
- Зависимость от доступности сервиса (если API down, ты не работаешь)
- Rate limits и quotas

**Когда использовать:**
- Development и prototyping
- Production если трафик низкий/средний
- Когда privacy не критична
- Когда нужна best-in-class модель (GPT-4 Turbo, Claude Opus)

### 2.2 Local Inference (llama.cpp, Ollama, vLLM)

**Преимущества:**
- Полный контроль (можешь модифицировать все)
- Privacy (данные остаются на твоем оборудовании)
- Zero latency (после загрузки модели)
- Никаких расходов после инвестиции в GPU
- Оффлайн работа (интернет не требуется)

**Недостатки:**
- Требуется оборудование (GPU с 8GB+ VRAM)
- Initial latency (загрузка модели в память)
- Меньшие модели (обычно 7B-70B параметров)
- Поддержка нужна самостоятельно (обновления, optimizations)
- Требуется техническая экспертиза

**Когда использовать:**
- High volume (cost effective после break-even)
- Privacy-sensitive данные
- Когда latency критична (real-time приложения)
- Развитые страны где GPU дешев
- Специализированные модели (fine-tuned для вашего домена)

### 2.3 Гибридный подход

Лучший выбор для многих приложений:

**Routing по сложности:**
- Simple task (классификация, extraction) → local Mistral 7B
- Medium task (кодирование, анализ) → cloud Sonnet
- Complex task (рассуждение, архитектура) → cloud Opus

**Fallback стратегия:**
- Сначала пробуем local
- Если timeout или ошибка → fallback to cloud
- Логируем какой path был использован

**Cost optimization:**
- Кэшируем результаты (если одинаковый input, не пересчитываем)
- Batching запросы (несколько за раз дешевле)
- Используем более дешевую модель для low-quality tasks

---

## 3. Open Source Models: Альтернативы Proprietary

### 3.1 Что такое GGUF и квантизация

**GGUF** — это формат для хранения моделей, оптимизированный для локального инференса. Позволяет:
- Компактное хранение (квантизованные веса)
- Быструю загрузку (streaming parts of model)
- Поддержку разных уровней квантизации

**Квантизация** — процесс уменьшения точности весов модели:
- FP32 (32-бит floats): полная precision, но большой размер
- FP16 (16-бит floats): хороший баланс
- Q8 (8-бит integers): дальнейшее сжатие
- Q4 (4-бит integers): очень маленький размер, некоторая потеря качества

**Практический выбор:**
- Q4_K_M: best default (4.3 bits, хороший balance)
- Q5_K_M: если качество критично
- Q3_K_M: если место критично (мобильные устройства)

### 3.2 Популярные open-source модели

#### Mistral 7B/12B

**Характеристики:** Открытая 7B модель, хорошее соотношение качество/размер.

**Использование:** General purpose, coding, instruction following.

**Когда:** Когда нужна легкая модель для local deployment.

#### LLaMA 3 (Meta)

**Характеристики:** Открытая 8B/70B, хорошо обучена на инструкции.

**Использование:** Base model для fine-tuning, local development.

**Когда:** Когда нужна базовая, проверенная модель.

#### Qwen Series (Alibaba)

**Характеристики:** Открытые 1B-32B моделямодели, хорошо обучены.

**Использование:** Multilingual support, coding, reasoning.

**Когда:** Когда нужна поддержка восточных языков.

#### DeepSeek

**Характеристики:** Открытая высококачественная модель для кодирования.

**Использование:** Code generation, code completion, debugging.

**Когда:** Когда основная задача — кодирование.

---

## 4. IDE и Editor Integration для AI

### 4.1 VS Code с AI Extensions

**Copilot:** Microsoft's AI assistant built into VS Code.

**Features:**
- Code completion (автополнение при печати)
- /generate: создать блок кода
- /explain: объяснить выбранный код
- /tests: генерировать unit tests
- Chat interface для диалога

**Setup:** Install "GitHub Copilot" extension, authenticate with GitHub.

### 4.2 JetBrains IDE Integration

IntelliJ, PyCharm, WebStorm поддерживают AI:

**Copilot for JetBrains:** Similar to VS Code, native integration.

**Gemini Code Assist:** Google's integration.

**Features:**
- /generate, /fix, /doc commands
- Chat в боковой панели
- Intelligent completions

**Setup:** Install plugin from JetBrains Marketplace.

### 4.3 Specialized IDE: Cursor

**Cursor** — это VS Code fork с встроенным AI, оптимизированным для работы с Claude.

**Features:**
- @claude mentions в chat
- Very good at understanding entire codebase
- CMD+K для inline editing
- CMD+SHIFT+K для create new file
- Trained specifically on working with agents

**Setup:** Download from cursor.sh.

---

## 5. Runtime Environments

### 5.1 Выбор между Cloud Runtime и Local

**Serverless (AWS Lambda, Cloudflare Workers):**
- Плюсы: платишь только за usage, масштабируется автоматически
- Минусы: холодный старт может быть медленным, контекст limited
- Когда: бюджетные приложения, unpredictable load

**Контейнеризация (Docker/Kubernetes):**
- Плюсы: полный контроль, reproducible deployment
- Минусы: нужен DevOps, сложнее чем serverless
- Когда: production, нужен контроль

**VPS/Dedicated Server:**
- Плюсы: дешево для predictable high load, полный контроль
- Минусы: нужно управлять инфраструктурой
- Когда: стабильный, высокий трафик

### 5.2 GPU Требования для Local Models

Таблица необходимой VRAM в зависимости от размера модели:

| Модель | Minimum VRAM | Recommended | Optimal |
|--------|--------------|-------------|---------|
| 7B | 8 GB | 12 GB | 24 GB |
| 13B | 12 GB | 16 GB | 40 GB |
| 30B | 24 GB | 40 GB | 80 GB |
| 70B | 40 GB | 80 GB | 2x80 GB |

**Квантизация помогает:** Q4 квантизация уменьшает требования примерно в 4 раза.

---

## 6. Decision Matrix: Какой стек выбрать

**Для стартапа (MVP):**
- Model: Claude Opus (best quality for ideas)
- Runtime: Cloudflare Workers (easy deployment)
- Storage: D1 (SQLite edge)
- Cost: ~$100-300/месяц

**Для production (medium traffic):**
- Model: Claude Sonnet (best balance)
- Runtime: Docker на VPS (full control, cost efficient)
- Storage: PostgreSQL (reliable, proven)
- Cost: ~$500-2000/месяц

**Для high-volume приложения:**
- Model: Mix (Haiku for simple, Sonnet for complex)
- Runtime: Kubernetes (auto-scaling)
- Storage: Multi-region database
- Cost: $5000+/месяц

**Для приватных данные:**
- Model: Mistral/LLaMA local
- Runtime: On-premise GPU servers
- Storage: Local databases
- Cost: $10000+ (для GPU)

---

## 7. Практические Рекомендации

### 7.1 Начните с облака

Облако лучше для:
- Экспериментирования (no setup)
- Понимания requirements (easy to measure cost)
- Доступа к лучшим моделям

После:
- Если стоимость очень высокая → перейдите на local
- Если performance критична → перейдите на local
- Если volume низкий → останьтесь на облаке

### 7.2 Оптимизация стоимости

**Низко висящие плоды:**
- Кэширование: сохраняйте результаты для одинаковых запросов
- Compression: используйте более дешевую модель для easy tasks
- Batching: обрабатывайте несколько запросов за раз

**Вложения:**
- Local inference если high volume
- Fine-tuning если специализированная задача
- Pruning/distillation для меньших моделей

### 7.3 Мониторинг выбора

Отслеживайте:
- Cost per request (тренд)
- Latency (TTFT, total time)
- Quality metrics (accuracy, user satisfaction)
- Error rate

Переоцените выбор если:
- Cost растет > 20% месяц-на-месяц без increase в usage
- Latency > требуемый threshold
- Quality degrading
- Error rate > 5%

---

## Резюме

Выбор модели и runtime — critical decision:

- **Cloud API** лучше для start: простая, лучшие модели, но дорого
- **Local inference** лучше для высокого volume: контроль и цена, но setup сложнее
- **Hybrid approach** часто best: используй оба в зависимости от задачи
- **Мониторь** cost и quality: регулярно переоцени выбор

Начните с облака (Claude Opus), поймите свои requirements, потом оптимизируйте.

---

# 07. Models & Runtime — Deep Dive (source-grounded)

## 1) Выбор модели = инженерный компромисс

Основные оси выбора:
- quality,
- latency,
- cost,
- privacy/compliance,
- tool ecosystem.

Нельзя выбирать модель «по хайпу» без матрицы критериев.

---

## 2) Runtime-стратегии

## 2.1 Cloud-first
Плюсы:
- быстрый старт,
- доступ к frontier моделям.

Минусы:
- стоимость на масштабе,
- ограничения по данным/комплаенсу.

## 2.2 Local/self-host
Плюсы:
- контроль данных,
- гибкость инфраструктуры.

Минусы:
- MLOps/infra нагрузка,
- ограничения по quality на части задач.

См.:
- `sources/lmstudio_overview.md`
- `sources/ollama_overview.md`

---

## 3) IDE/CLI слой как часть runtime

Практика показывает рост значения terminal-first и IDE-integrated агентов:
- Cursor CLI,
- Gemini Code Assist,
- Qoder/Warp и т.д.

Задача — не «какой инструмент моднее», а насколько он:
- интегрирован в пайплайн,
- контролируем по policy,
- воспроизводим в команде.

См.:
- `sources/cursor_cli_overview.md`
- `sources/google_gemini_code_assist_write_code.md`
- `sources/qoder_overview.md`
- `sources/warp_overview.md`

---

## 4) Decision matrix (обязательная)

Для каждого use-case оцени:
1. Accuracy criticality,
2. Data sensitivity,
3. Budget per task,
4. SLA (latency),
5. Требования к tool-use.

Итог: 1 primary + 1 fallback runtime.

---

## 5) Антипаттерны

1. Один модельный стек на все задачи.
2. Нет fallback при деградации провайдера.
3. Нет контроля стоимости на уровне сценария.
4. Инструменты не стандартизированы между участниками команды.

---

## 6) Lab

Собери таблицу по 3 сценариям:
- coding feature delivery,
- long-form research,
- private data assistant.

Для каждого:
- primary model/runtime,
- fallback,
- expected cost,
- expected latency,
- risk notes.

Deliverable: `model-selection-matrix.md`.

---

## 7) Source anchors

- `sources/lmstudio_overview.md`
- `sources/ollama_overview.md`
- `sources/cursor_cli_overview.md`
- `sources/google_gemini_code_assist_write_code.md`
- `sources/qoder_overview.md`
- `sources/warp_overview.md`
