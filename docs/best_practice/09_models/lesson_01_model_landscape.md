---
module: "09_models"
lesson: 1
title: "Ландшафт моделей 2025-2026"
type: "theory"
prerequisites: []
difficulty: "beginner"
tags: ["models", "claude", "gpt", "gemini", "llama", "comparison", "selection"]
---

# Ландшафт моделей 2025-2026

## Введение

В 2025-2026 годах разработчики сталкиваются с беспрецедентным выбором языковых моделей. Правильный выбор модели -- это инженерный компромисс между quality, latency, cost, privacy и tool ecosystem. Выбирать модель "по хайпу" без матрицы критериев -- антипаттерн.

Этот урок охватывает ландшафт доступных моделей и учит принимать обоснованные решения о выборе.

---

## 1. Главные игроки

### 1.1 Claude (Anthropic)

Семейство Claude предлагает три модели с разными точками оптимизации:

| Модель | Context | Лучше всего для |
|--------|---------|-----------------|
| Claude Opus 4.6 | 200K | Сложные рассуждения, архитектура, глубокий анализ |
| Claude Sonnet 4.5 | 200K | Production, баланс quality/speed, повседневная разработка |
| Claude Haiku 4.5 | 200K | Быстрые задачи, streaming, масштабирование |

**Когда использовать Claude:**
- Сложные инженерные задачи, требующие глубокого анализа
- Production-системы, где важны reliability и safety
- Работа с большим контекстом (200K токенов достаточно для целых кодовых баз)

**Соотношение цена/производительность:**
- **Opus** -- самый дорогой, лучшее качество рассуждений и анализа
- **Sonnet** -- ~2x быстрее Opus с минимальной потерей качества. Рабочая лошадка для production
- **Haiku** -- ~5x быстрее Sonnet, оптимален для простых задач на масштабе

### 1.2 GPT-4o и o-серия (OpenAI)

OpenAI предлагает две линейки:

**GPT-4o** -- сильная multimodal модель (текст, изображения, видео, аудио).

Когда использовать:
- Работа с изображениями (vision capabilities)
- Мультимодальные приложения
- Когда нужна экосистема OpenAI (DALL-E, Whisper, TTS)

**o1 / o3** -- модели, специально обученные extended reasoning (chain-of-thought).

Когда использовать:
- Задачи, требующие длинных цепочек рассуждений
- Математика, формальная верификация
- Когда latency не критична (reasoning занимает время)

### 1.3 Gemini (Google)

Семейство моделей с фокусом на multimodal и огромный context window.

Когда использовать:
- Очень большой контекст (1M+ токенов)
- Бюджетные приложения (Gemini Flash очень дёшев)
- Интеграция с сервисами Google
- Бесплатный tier для прототипирования (60 req/min, 1000 req/day)

### 1.4 Специализированные модели

**Для кодирования:**
- **DeepSeek Coder** -- открытая модель, высокое качество code generation
- **Mistral Code** -- специализирована для code completion
- **Kimi K2** (MoonshotAI) -- MoE архитектура (1T параметров, 32B активных), оптимизирована для агентов и tool-calling
- **Qwen-Code** (Alibaba) -- от 7B до 235B, сильна в анализе кодовых баз

**Для reasoning:**
- **o1/o3** (OpenAI) -- специально обучены длительному reasoning
- **DeepSeek-R1** -- открытая альтернатива o1

---

## 2. Критерии выбора модели

### 2.1 Пять осей выбора

При выборе модели оценивайте пять ключевых параметров:

**Quality (качество вывода):**
- MMLU score -- общие знания
- LiveCodeBench -- способность писать рабочий код
- SWE-bench -- решение реальных GitHub issues (критично для агентов)
- Math reasoning -- математические рассуждения

**Latency (скорость):**
- TTFT (Time To First Token) -- задержка до первого токена (100-500ms для облачных API)
- TPS (Tokens Per Second) -- скорость генерации (30-100 для облака)

**Cost (стоимость):**
- Input tokens дешевле, output tokens дороже
- Для high-volume приложений cost может стать доминирующим фактором

**Privacy / Compliance:**
- Данные отправляются в облако или остаются локально?
- Требования регулятора (GDPR, HIPAA)
- Необходимость air-gapped deployment

**Tool Ecosystem:**
- Качество tool-calling (function calling)
- Поддержка MCP (Model Context Protocol)
- Интеграция с IDE и CI/CD

### 2.2 Матрица выбора

```
                  Quality-focused      Cost-focused        Speed-focused
Simple Task      Haiku/Gemini Flash   Haiku/Mistral 7B    Haiku/Flash
Medium Task      Sonnet               Mistral 7B          Sonnet
Complex Task     Opus/o1              DeepSeek Coder      Sonnet
Coding           DeepSeek Coder       Mistral Code        Haiku
Multimodal       GPT-4o               Gemini Flash        GPT-4o
Reasoning        o1/DeepSeek-R1       (не рекомендуется)  (не рекомендуется)
```

### 2.3 API совместимость

Три основных стандарта API:

- **OpenAI-совместимый API** -- де-факто стандарт; поддерживается большинством открытых моделей через llama.cpp, Ollama, vLLM
- **Anthropic API** -- для Claude; свой формат, но хорошо документирован
- **Google API** -- для Gemini; proprietary, но есть SDK для всех языков

Многие фреймворки (LangChain, LiteLLM, Vercel AI SDK) абстрагируют различия, позволяя переключаться между провайдерами без переписывания кода.

---

## 3. Open-source модели

### 3.1 Зачем нужны открытые модели

Открытые модели не заменяют frontier-модели (Claude Opus, GPT-4o), но покрывают важные сценарии:

- **Privacy** -- данные не покидают ваш сервер
- **Cost** -- после инвестиции в GPU расходы на inference минимальны
- **Offline** -- работают без интернета
- **Fine-tuning** -- можно дообучить на вашем домене
- **Customization** -- полный контроль над параметрами и поведением

### 3.2 Ключевые семейства

#### Mistral (7B / 12B)

Открытая модель с хорошим соотношением качество/размер. General purpose: кодирование, instruction following, анализ. Оптимальна для local deployment на consumer hardware.

#### LLaMA 3 (Meta, 8B / 70B)

Хорошо обучена на инструкциях. Проверенная base model для fine-tuning. Широкая экосистема: огромное количество fine-tuned вариантов на Hugging Face.

#### Qwen (Alibaba, 1B-72B)

Multilingual support (особенно восточные языки). Coding и reasoning. Хорошо масштабируется от мобильных устройств (1B) до серверов (72B).

#### DeepSeek

Высококачественная модель для кодирования. Code generation, completion, debugging. DeepSeek-R1 -- открытый аналог o1 для reasoning.

### 3.3 Формат GGUF и квантизация

**GGUF** (GGML Universal Format) -- стандартный формат для локального inference. Позволяет компактно хранить квантизованные веса и быстро загружать модель.

**Квантизация** -- уменьшение точности весов для экономии памяти:

| Формат | Бит | Качество | Рекомендация |
|--------|-----|----------|--------------|
| Q4_K_M | 4.3 | Хороший баланс | По умолчанию |
| Q5_K_M | 5.3 | Выше качество | Когда качество критично |
| Q8_0 | 8 | Почти без потерь | Критичные приложения |
| Q3_K_M | 3 | Минимальный размер | Мобильные устройства |

**Практическое правило:** Q4_K_M -- best default для большинства задач. Потеря качества минимальна, а экономия памяти ~4x по сравнению с FP16.

---

## 4. IDE и CLI как часть выбора стека

### 4.1 IDE-integrated агенты

Выбор модели неразрывно связан с инструментами разработки:

**VS Code + Copilot** -- code completion, `/generate`, `/explain`, `/tests`, chat interface. Работает с GPT-4 и Claude.

**JetBrains + AI Assistant** -- аналогичные возможности для IntelliJ, PyCharm, WebStorm. Поддержка Copilot и Gemini Code Assist.

**Cursor** -- VS Code fork с глубокой интеграцией Claude. `@claude` mentions, CMD+K inline editing, понимание всей кодовой базы.

### 4.2 Terminal-first агенты

Растёт значение CLI-агентов:

- **Claude Code** -- Anthropic's официальный CLI
- **Gemini CLI** -- open-source (Apache 2.0), бесплатный tier, Google Search встроен
- **Cursor CLI** -- доступ к frontier-моделям из терминала
- **Qoder, Warp** -- специализированные terminal-агенты

### 4.3 Критерии выбора инструмента

Задача -- не "какой инструмент моднее", а насколько он:

- **Интегрирован в ваш pipeline** (CI/CD, Git workflow)
- **Контролируем по policy** (лимиты, доступ, аудит)
- **Воспроизводим в команде** (одинаковый setup у всех разработчиков)

---

## 5. Decision Matrix: обязательная практика

### 5.1 Для каждого use-case оцените

1. **Accuracy criticality** -- насколько критична точность вывода?
2. **Data sensitivity** -- можно ли отправлять данные в облако?
3. **Budget per task** -- сколько можно потратить на один запрос?
4. **SLA (latency)** -- какая допустимая задержка?
5. **Tool-use requirements** -- нужен ли function calling, MCP?

Итог: **1 primary model + 1 fallback runtime** для каждого сценария.

### 5.2 Рекомендации по стеку

**Для стартапа (MVP):**
- Model: Claude Opus (лучшее качество для прототипа)
- Fallback: Claude Sonnet
- Cost: ~$100-300/месяц

**Для production (medium traffic):**
- Model: Claude Sonnet (баланс quality/cost)
- Fallback: Haiku или local Mistral для простых задач
- Cost: ~$500-2000/месяц

**Для high-volume приложений:**
- Model: Mix -- Haiku для простых, Sonnet для сложных задач
- Fallback: local inference (Ollama + Mistral/LLaMA)
- Cost: $5000+/месяц

**Для приватных данных:**
- Model: Mistral / LLaMA local
- Runtime: on-premise GPU
- Cost: $10000+ начальная инвестиция в hardware

---

## 6. Антипаттерны

1. **Одна модель на все задачи** -- нет универсального решения. Routing по сложности экономит деньги и время.
2. **Нет fallback при деградации провайдера** -- API может быть недоступен. Всегда имейте план B.
3. **Нет контроля стоимости на уровне сценария** -- без budget tracking один агент может сжечь месячный бюджет за день.
4. **Инструменты не стандартизированы в команде** -- разные настройки у разных разработчиков ведут к невоспроизводимым результатам.
5. **Выбор модели по бенчмаркам без проверки на своих данных** -- бенчмарки не всегда отражают performance на вашем домене.

---

## Резюме

Выбор модели -- это инженерное решение по пяти осям:

- **Quality** -- какое качество вывода необходимо
- **Latency** -- допустимая задержка
- **Cost** -- бюджет на inference
- **Privacy** -- требования к данным
- **Ecosystem** -- tool-calling, IDE, CI/CD интеграция

Начните с облака (Claude Sonnet/Opus) для понимания requirements, затем оптимизируйте: добавьте routing по сложности, local fallback, кэширование. Регулярно переоценивайте выбор -- ландшафт моделей меняется каждые 3-6 месяцев.

---

## Далее

В следующем уроке ([lesson_02](lesson_02_local_cloud_runtime.md)) рассмотрим практику: локальный inference с llama.cpp и Ollama, облачные coding assistants, гибридные стратегии и оптимизацию производительности.
