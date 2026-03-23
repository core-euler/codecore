# LLM-Driven Development: Best Practices & Toolkit

> Выжимка полезной информации из ТГ-канала «Вайб-кодинг» (821 сообщение, май — ноябрь 2025), актуализированная по состоянию на **февраль 2026**. Отфильтровано от мемов, рекламы и шума. Только применимые практики, инструменты и ресурсы для LLM-разработчика.

---

## 1. AI-IDE и редакторы кода

### 1.1 Cursor

> **Актуальная версия: 2.4.x (февраль 2026).** Собственная модель Composer обновлена до v1.5 (в 2x быстрее Sonnet 4.5). BugBot достиг 70% resolution rate и получил автофикс через Cloud Agents. Поддерживается параллельный запуск до 8 агентов.

Cursor — наиболее часто упоминаемый AI-редактор. Основные советы:

**Рабочее пространство с несколькими проектами:**
Создай файл `.code-workspace`, добавь `"folders"` и `"settings"`, открой как workspace — получишь обмен данными между проектами.

**Background Agent (Cmd/Ctrl+E):**
Фоновые агенты работают асинхронно — можно поручить несколько тасок отдельным экземплярам и продолжать работать над другими.

**MCP в один клик:**
MCP-серверы добавляются через список на [docs.cursor.com/tools](https://docs.cursor.com/tools) или по ссылке + OAuth.

**Команда `/compress`:**
Освобождает место в контекстном окне когда оно заполняется. Рекомендуется использовать при ~50% заполнении контекста.

**Команда `/summarize`:**
Аналогично, экономит деньги и держит ответы чёткими.

**Правила для Mermaid-диаграмм:**
Добавь правило в user rules: `explain with colored mermaid diagrams` — получай визуальные объяснения.

**Git worktree:**
Cursor нативно поддерживает git worktree — можно запускать несколько агентов параллельно, у каждого изолированная копия репо.

**Custom hooks (v1.7+):**
Расширяй и скриптуй любой этап жизненного цикла Cursor-агента.

**Вайбкодинг-пайплайн через Cursor:**
```
gitsearchai.com — найти вдохновляющий репозиторий
↓
gittodoc.com — превратить репо в документацию
↓
Cursor — скормить документацию и попросить собрать проект
```

**Связка Cursor + Traycer:**
1. Пишешь TraycerAI (traycer.ai) что хочешь сделать
2. Смотришь визуализацию плана
3. Реализуешь в Cursor
4. Получаешь MVP с первого захода

**Cursor CLI:** [cursor.com/cli](https://cursor.com/cli)
Поддерживает MCP-серверы через `.cursor/mcp.json`, проверка изменений по Ctrl+R, `@`-упоминание файлов, AGENTS.md и CLAUDE.md.

**Бесплатный курс от Cursor:** [cursor.com/ru/learn](https://cursor.com/ru/learn) — ~1 час, паттерны запросов, интерактивные задания.

**Cursor 2.0 → 2.4 (актуально):** Собственная модель Composer 1.5 (RL, self-summarization, thinking tokens), параллельные агенты (до 8 штук), встроенный браузер, голосовой режим. Multi-Agent Interface позволяет каждому агенту работать в изолированном окружении.

### 1.2 Claude Code

> **Актуально (февраль 2026):** Claude Code работает на Opus 4.6 с контекстом 1M токенов (бета). Появились Agent Teams (research preview) для мультиагентной коллаборации и автоматический recall памяти. Structured Outputs теперь GA. Claude Agent SDK доступен на Python и TypeScript, интегрирован в Apple Xcode 26.3.

**Слэш-команды:**
Создавай кастомные промпты в виде Markdown-файлов в `.claude/commands/` и вызывай через `/your-command`. Поддерживают bash-команды, `@`-упоминания файлов, расширенное мышление.

**Подагенты:**
Просто попроси Claude Code запустить подагентов — он сможет выполнять несколько задач одновременно. Например, один делает аудит безопасности, другой ищет несоответствия в UI.

```
# Формальная система подагентов
docs: https://docs.anthropic.com/en/docs/claude-code/sub-agents
```

**Playwright MCP для тестирования UI:**
```bash
claude mcp add playwright npx '@playwright/mcp@latest'
```
После этого можно просить: «протестируй кнопку на моей главной с помощью playwright mcp».

**Мониторинг токенов:**
- [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) — реалтайм отслеживание потребления и burn rate
- Команда `/context` (v1.0.86+) — визуализация контекстного окна и использования токенов

**Настройки безопасности (`~/.claude/settings.json`):**
Задай список доверенных инструментов для автоматического разрешения — агент будет запрашивать разрешение только на критичные действия.
Пример: https://gist.github.com/iannuttall/a7570cee412cc05d32d7a039830f28c7

**Несколько директорий в одной сессии:**
```
/add-dir <путь>
```
Полезно для монорепозиториев, общих настроек и кросс-проектной работы.

**Режим планирования (Opus plan mode):**
`/model` → выбрать «Opus plan mode». Opus 4.6 для планирования + Sonnet 4.5 для выполнения. Переключение между режимами: `Shift+Tab`.

**Фоновые задачи:**
Claude Code умеет крутить bash-команды в фоне и в реальном времени смотреть логи. Если что-то ломается — проходится по логам и помогает починить.

**Промпт-хуки (v2.0+):**
```
PreToolUse: запретить правки в .env
PreCompact: сохранить транскрипт перед сжатием
SessionStart: подгрузить git status и последние задачи
Stop: запустить тесты
```
Docs: https://code.claude.com/docs/en/hooks

**Skills:**
Один из самых мощных способов управлять поведением Claude Code. Система контекстного тирования позволяет эффективно использовать токены. Skills хорошо дополняют MCP и субагентов.
Docs: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview

**Плагины:**
```bash
/plugin marketplace add anthropics/claude-code
/plugin install feature-dev
```
Любой может разместить свой маркетплейс — достаточно git-репозитория с `.claude-plugin/marketplace.json`.

**Настройка стиля вывода:**
`/output-style` — выбрать режим обучения (лёгкий или learn-by-doing). Или `@agent-output-style-setup` для кастомизации.

**Claude Code SDK (Python):**
```
https://github.com/anthropics/claude-code-sdk-python
```
Использовать Claude Code программматически в собственных инструментах и агентах.

**Claude Code Agent SDK:**
Доступ к тем же инструментам и системам управления контекстом, что и у Claude Code. Доступен на Python и TypeScript, интегрирован нативно в Apple Xcode 26.3.
https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

**Шпаргалка по Claude Code (10 уровней):**
https://github.com/Njengah/claude-code-cheat-sheet

**Claude Code Cheat Sheet промпт «Always Works™»:**
```
Базовая философия:
- "Должно работать" ≠ "Работает"
- Нетестированный код — всего лишь догадка
- 30-секундная проверка: запускал? вызвал фичу? увидел результат?

Фразы, которых стоит избегать:
- "Теперь должно работать"
- "Я пофиксил" (если уже не первый раз)
- "Попробуй сейчас" (не попробовав сам)

Требования к тестированию:
- UI: реально кликни кнопку
- API: сделай настоящий запрос
- Данные: проверь запросом базу
- Конфиг: перезапусти и убедись
```

**Life OS на Claude Code:**
Кастомные слэш-команды: `/researcher` для анализа конкурентов, `/daily_brief` для новостей, `/brain_dump` для поиска паттернов в заметках.

**Запуск Claude Code в Docker:**
```bash
npx claude-code-templates@latest --sandbox docker \
  --agent development-team/backend-architect \
  --prompt "Create a REST API with Express"
```

**Аналитика сессий:**
```bash
npx claude-code-templates@latest --chats
```
Токены, вызовы тулов, эффективность кэша, стоимость.

**Decode (Anthropic):**
Объединяет Claude Code с браузером и интерактивным whiteboard. Просмотр нескольких экранов как в Figma, UX-фидбэк во время разработки, infinite canvas для экспериментов.
https://decode.dev

### 1.3 Другие AI-IDE

**Gemini Code Assist (бесплатно):**
- Gemini 2.5, 240 чатов/день, 180K автодополнений/месяц
- Agent mode: Settings → `"geminicodeassist.updateChannel": "Insiders"`
- https://developers.google.com/gemini-code-assist/docs/write-code-gemini

**Gemini CLI (open-source):**
- 60 запросов/мин и 1000/день бесплатно (подтверждено на февраль 2026 — крупнейшая бесплатная квота в индустрии)
- Контекст 1M токенов
- Расширения: `gemini extensions install <GitHub URL>`, маркетплейс с 70+ расширениями
- Поддержка PTY для интерактивных команд (vim, top, git rebase -i)
- Jules доступен как расширение: `/jules добавь кнопку логина`
- https://github.com/google-gemini/gemini-cli

**OpenCode — альтернатива Claude Code:**
- Open-source, работает с локальными моделями
- Совместим с Copilot, OpenAI, Anthropic, Google
- 75+ LLM-провайдеров, zero config
- https://github.com/sst/opencode

**GitHub Copilot CLI:**
ИИ-ассистент в терминале, поддержка всех топовых моделей.

**Codex (OpenAI) в VS Code:**
Расширение «Codex – OpenAI's coding agent», режимы Local/Cloud, Agent mode, модели GPT-5 и GPT-5.3-Codex.

**Kiro (Amazon):**
Поддержка Claude 3.7 и 4 Sonnet, режимы Agent Chat/Hooks/Steering. По-прежнему в Public Preview (февраль 2026). После GA — тарифы FREE ($0) и PRO+ ($39/мес). http://kiro.dev

**Qoder (Alibaba):**
Чат для парного программирования, умное переключение моделей — https://qoder.com/download

**Warp 2.0:**
Терминал + AI-агент. Собственный агент для написания кода и изменения файлов — https://www.warp.dev/

---

## 2. MCP (Model Context Protocol)

### 2.1 Что это и зачем

> **Актуально (февраль 2026):** MCP стал индустриальным стандартом. В декабре 2025 Anthropic передала протокол в Agentic AI Foundation (AAIF) под Linux Foundation. Со-основатели: OpenAI и Block. Участники: AWS, Google, Microsoft, Cloudflare, Bloomberg. 10 000+ серверов опубликовано.

MCP — протокол для подключения AI-агентов к внешним инструментам. Экосистема протоколов:
- **MCP** — подключает агентов к инструментам
- **A2A** — соединяет агентов между собой
- **AG-UI** — связывает агентов с пользовательским интерфейсом (активно развивается CopilotKit, интегрирован в ASP.NET Core)

### 2.2 Топ MCP-серверы

1. **Filesystem** — чтение, запись и поиск файлов локально
2. **Playwright** — автоматизация браузера (самый популярный!)
3. **Run Python** — выполнение Python-кода через Deno + Pyodide
4. **GitHub** — управление репозиториями через чат
5. **Notion** — чтение/запись задач, заметок, баз данных
6. **Tavily** — поиск в интернете в реальном времени
7. **mem0** — слой памяти агента
8. **Chrome DevTools MCP** — AI видит браузер, отлаживает стили, находит баги
9. **Jupyter MCP** — управление Jupyter-ноутбуками через Claude
10. **Chart MCP** — 20+ визуализаций данных: https://github.com/antvis/mcp-server-chart

**Chrome DevTools MCP:**
AI может открывать браузер, видеть эффекты, находить баги, предлагать улучшения.
https://developer.chrome.com/blog/chrome-devtools-mcp

### 2.3 Каталоги MCP-серверов

- **awesome-mcp-servers (1200+ проверенных):** https://github.com/punkpeye/awesome-mcp-servers
- **GitHub MCP Registry (40+ курируемых от Figma, Postman, Stripe, Microsoft и др.):** https://github.com/mcp
- **Дополнительные каталоги:** mcpservers.org, mcp.so, mcpmarket.com
- **VS Code MCP:** https://code.visualstudio.com/mcp — теперь поддерживает MCP Apps (интерактивные UI прямо в IDE)
- **Курс от Microsoft «MCP для начинающих» (9 модулей, .NET/Java/TS/JS/Rust/Python):** https://github.com/microsoft/mcp-for-beginners
- **Курс от Cloudflare:** https://learnmcp.examples.workers.dev

### 2.4 Создание MCP-серверов

**Быстрый способ:** скачай FastMCP через `gitIngest`, передай в FactoryAI и укажи, какой MCP-сервер нужен.

**Преврати GitHub-репо в MCP-сервер:**
Замени `github.com` на `gitmcp.io` в URL — получишь готовый MCP-сервер с конфигом для IDE.

**Универсальный MCP-сервер RUBE:**
500+ интеграций, работает с любым хостом MCP, строит пайплайны на основе запроса.
https://rube.so/

**MCP Manager (GUI):**
https://github.com/namuan/py-mcp-manager

**mcp-use — подключение любого LLM к любому MCP-серверу:**
Работает с Ollama, LangChain, полностью локально.
https://github.com/mcp-use/mcp-use

**MCP Inspector — понять как работает MCP изнутри:**
```bash
npx -y @modelcontextprotocol/inspector npx chrome-devtools-mcp@latest
```

### 2.5 Практика MCP + память

**Graphiti MCP — общий слой памяти для Claude Desktop + Cursor:**
Строит живой временной граф знаний. Можно болтать с Claude Desktop, сохранять в память, а доставать из Cursor.
https://github.com/getzep/graphiti

**Code Context — семантический поиск по коду через MCP:**
Полная индексация кодовой базы для более глубокого контекста.
https://github.com/zilliztech/code-context

---

## 3. Промпт-инженерия и Context Engineering

### 3.1 Agentic Context Engineering (ACE) — Stanford

> **Актуально (февраль 2026):** ACE перешёл из исследовательской фазы в раннее промышленное внедрение. SambaNova выпустила полную open-source реализацию. Сообщество создаёт собственные имплементации (kayba-ai/agentic-context-engine).

Революционный подход: вместо fine-tuning модель развивает сам контекст. Модель пишет, анализирует и переписывает собственный промпт через цикл: генерация → рефлексия → курирование.

Результаты: +10.6% vs GPT-4-агенты, +8.6% в финансовом домене, на 86.9% дешевле и быстрее.

Вместо «коротких и чистых» промптов ACE строит длинные, эволюционирующие «плейбуки».
Paper: https://www.arxiv.org/abs/2510.04618
Open-source реализация от SambaNova: https://sambanova.ai/blog/ace-open-sourced-on-github/

### 3.2 Практические советы по Context Engineering

1. **Порядок контекста важен:** используйте «append-only» — добавлять новую информацию в конец. Увеличивает попадания в кэш (снижает стоимость в ~4 раза).
2. **Управляйте инструментами статично:** не меняйте порядок/доступность тулов в процессе задачи.
3. **Используйте внешнюю память:** записывайте контекст/цели во внешнее хранилище.
4. **Повторяйте цели:** периодически заставляйте модель проговаривать свои цели.
5. **Принимайте ошибки:** сохраняйте сообщения об ошибках в контексте — модель учится на них.

### 3.3 Промпт-библиотека

**SearchPromptly.com** — 999+ тщательно проработанных промптов, бесплатно.

**Утёкшие системные промпты ChatGPT, Gemini, Claude, Grok:**
https://github.com/asgeirtj/system_prompts_leaks

### 3.4 CLAUDE.md и AGENTS.md

Anthropic рекомендует подключать `AGENTS.md` прямо внутри `CLAUDE.md`. Инструмент для автоматизации:
https://github.com/iannuttall/source-agents

**Ruler — единые правила для AI-кодинга:**
Объединяет `.cursor/rules/`, `CLAUDE.md`, `AGENT.md` в одну папку `.ruler/`.
https://github.com/intellectronica/ruler

### 3.5 Выход из «AI-цикла»

Когда агент застрял, попросите его:
1. Придумать 5 вариантов рефакторинга
2. Оценить каждый
3. Выбрать самый надёжный

### 3.6 Двойная проверка (Cross-review)

**Сетап: Codex слева, Claude Code справа**
1. Начинай разработку в Claude Code в режиме планирования
2. Копируй план в Codex, проверяй
3. Если один облажался — передай второму
4. После каждого изменения — проси второго сделать ревью

---

## 4. LLM-модели — обзор актуальных

> **Обновлено: февраль 2026.** Ландшафт моделей значительно изменился с момента исходных постов. Ниже актуальное состояние.

### 4.1 Claude (Anthropic)

- **Claude Opus 4.6** (новинка) — первая модель Opus с контекстом 1M токенов (бета), первый AI с 80%+ на SWE-bench Verified (80.9%)
- **Claude Opus 4.5** — по-прежнему доступен, 80.9% SWE-bench
- **Claude Sonnet 4.5** — лучшая сбалансированная модель для кодинга, 77.2% SWE-bench, может работать автономно 30+ часов
- **Claude Haiku 4.5** — 2x быстрее и 3x дешевле Sonnet 4.5, $1/$5 за 1M токенов
- **Structured Outputs** — теперь **GA** (не бета!) для Sonnet 4.5, Opus 4.5, Haiku 4.5, Opus 4.6

### 4.2 GPT (OpenAI)

- **GPT-5.3-Codex** (новинка, 5 февраля 2026) — самая мощная агентная модель для кодинга, на 25% быстрее GPT-5.2-Codex
- **GPT-5.2** — модель для профессиональной работы с документами, кодом, длинными контекстами
- **GPT-5** — остаётся базовой интегрированной моделью для всех пользователей (включая бесплатных)
- **gpt-oss-120b / gpt-oss-20b** — open-source, Apache 2.0. 120b: 117B параметров (5.1B активных), работает на одном 80GB GPU. 20b: 21B параметров, работает на 16GB устройствах. Доступны через HuggingFace, vLLM, Ollama, llama.cpp, LM Studio
- **Atlas** — AI-браузер ChatGPT, доступен на macOS для Free/Plus/Pro/Go. Агентный режим, контекстная память, вкладки

### 4.3 Gemini (Google)

- **Gemini 3 Pro** (ноябрь 2025) — контекст 1M токенов, #1 на LMArena (1501 Elo), значительно обходит 2.5 Pro
- **Gemini 3 Deep Think** — расширенная версия для глубокого рассуждения (ролаут начала 2026)
- **Gemini CLI** — бесплатно, 60 req/мин, расширения, маркетплейс

### 4.4 Open-Source модели

- **Kimi K2.5** (январь 2026) — новая мультимодальная версия с улучшенными агентными способностями. K2 Thinking по-прежнему лидер: SWE-bench 71.3%, $0.60/$2.50 за 1M токенов. https://github.com/MoonshotAI/Kimi-K2
- **Qwen3-Coder-Next** (февраль 2026) — всего 3B активных параметров (80B total), но сравним с моделями в 10-20x крупнее. Контекст 256K. Qwen Code CLI: 1000 бесплатных запросов/день. https://github.com/QwenLM/qwen-code
- **DeepSeek-V3.2** — один из лучших open-source для рассуждений, на уровне проприетарных моделей. DeepSeek-R1-0528 по-прежнему доступен
- **MiniMax M2.1** (декабрь 2025) — обновлённая версия для мультиязычного программирования. M2.2 ожидается в февврале 2026. Open-source веса
- **GLM-4.7** — лидер на SWE-bench для сложных кодовых баз

### 4.5 Запуск моделей локально

**LM Studio:** https://lmstudio.ai — GUI для локального запуска моделей
**Ollama:** стриминг с tool calling, веб-поиск в реальном времени. https://ollama.com
**llama.cpp:** 150K+ моделей GGUF, веб-UI похожий на ChatGPT. https://github.com/ggml-org/llama.cpp

**Claude Code с локальным LLM:**
Через vLLM + прокси можно запустить Claude Code на любом локальном LLM.

---

## 5. RAG (Retrieval-Augmented Generation)

### 5.1 RAG для кода

**Graph-Code RAG:**
Граф-ориентированная система вместо naive chunking. Учитывает дальние зависимости и перекрёстные ссылки.
https://github.com/vitali87/code-graph-rag

**Code Context MCP:**
Семантический поиск по кодовой базе для Claude Code.
https://github.com/zilliztech/code-context

### 5.2 Продвинутые RAG-подходы

**Chunk-On-Demand (Elysia):**
Не разбивает документы на чанки заранее — делает это только когда документ нужен. Снижает хранение, улучшает качество.
https://elysia.weaviate.io

**ColiVara — RAG без чанкинга:**
Документы обрабатываются как картинки через vision-модель. Точность выше классических RAG.

**Airweave — живые базы знаний:**
Би-временная база для агентов, семантический + ключевой поиск, 30+ источников.
https://github.com/airweave-ai/airweave

### 5.3 Гибридный RAG + Text2SQL

Классификация запросов для маршрутизации между SQL и векторным поиском + генерация ответов с контекстным обогащением.
https://github.com/patchy631/ai-engineering-hub/tree/main/rag-sql-router

### 5.4 Site-to-RAG

Превращает любой сайт в данные для RAG — чистые, структурированные фрагменты с тегами.
https://github.com/hyperbrowserai/examples/tree/main/site2rag

### 5.5 Gemini File Search API

> **Актуально (февраль 2026):** По-прежнему в Public Preview (не GA). Запущен в ноябре 2025 как встроенный RAG в Gemini API.

Полностью управляемая RAG-система прямо внутри Gemini API. Семантический + ключевой поиск по кодовым базам, без сложной настройки. Платить только за индексацию.
https://ai.google.dev/gemini-api/docs/file-search

---

## 6. Фреймворки для AI-агентов

### 6.1 CrewAI — 12 инструментов для агентов

> **Актуально (февраль 2026):** CrewAI v1.9.x, 100K+ сертифицированных разработчиков, Series A ($18M). По-прежнему один из лидеров для мультиагентных систем.

FileReadTool, FileWriterTool, CodeInterpreterTool, ScrapeWebsiteTool, SerperDevTool, DirectoryReadTool, FirecrawlSearchTool, BrowserbaseLoadTool, PDFSearchTool, GithubSearchTool, TXTSearchTool, L2SQLTool.
Docs: https://docs.crewai.com

### 6.2 SuperClaude

Фреймворк для Claude Code: память с контрольными точками (Git), 9 агентных персон, сверка с документацией, на 70% эффективнее по токенам.
https://github.com/NomenAK/SuperClaude

### 6.3 LangChain Deep Agents

> **Актуально (февраль 2026):** Доступен на Python и TypeScript. Используется в Deep Research, Manus, Claude Code. Активно обновляется (январь 2026).

Библиотека, превращающая любую LLM в «глубоко думающего» агента с MCP. Поддерживает планирование задач, управление контекстом файловой системы, спавн подагентов, долгосрочную память.
https://github.com/langchain-ai/deepagents

### 6.4 AG-UI Protocol

Протокол взаимодействия агентов с UI. Стриминг обновлений на уровне токенов, прогресс инструментов, общее состояние, паузы.
```bash
npx create-ag-ui-app my-agent-app
```
https://github.com/ag-ui-protocol/ag-ui

### 6.5 Motia

Унифицированная система: API, фоновые задачи, события и агенты — это шаги. Python, JS и TypeScript в одном процессе.
https://github.com/MotiaDev/motia

### 6.6 DeepMCPAgent

Plug-and-play фреймворк для MCP-агентов с LangChain/LangGraph.
https://github.com/cryxnet/deepmcpagent

### 6.7 Microsoft Agent Lightning

Оптимизация multi-agent систем: RL, автоматическая оптимизация промптов, supervised fine-tuning.
https://github.com/microsoft/agent-lightning

### 6.8 OpenAI AgentKit (октябрь 2025)

Полный фреймворк для построения AI-агентов от OpenAI. Визуальный Agent Builder (канва), Connector Registry, ChatKit для интерфейсов, Evals for Agents для измерения производительности. Решает проблему вывода агентов в продакшн.
https://openai.com/index/introducing-agentkit/

### 6.9 Composio — 850+ интеграций для агентов

Open-source платформа: 850+ готовых коннекторов для AI-агентов, поддержка 25+ агентных фреймворков. Управляет OAuth 2.0, API-ключами, аутентификацией. Реалтайм мониторинг выполнения инструментов.
https://github.com/ComposioHQ/composio

### 6.10 Spec Kit (GitHub)

> **Актуально (февраль 2026):** 50K+ звёзд на GitHub за пару месяцев. Один из самых чистых spec-first подходов без vendor lock-in.

Решает проблему «vibe-based programming» — сначала формулируешь задачу, потом передаёшь AI. Поддерживает Claude Code, Gemini CLI, Cursor, Copilot, Windsurf. Включает Specify CLI для бутстрапинга проектов.
https://github.com/github/spec-kit

---

## 7. Память агентов

### 7.1 Zep / Graphiti

> **Актуально (февраль 2026):** Версия 0.27.x (pre-release). Опубликована научная статья «Zep: A Temporal Knowledge Graph Architecture for Agent Memory» (январь 2026). Би-темпоральная модель: отслеживает и когда событие произошло, и когда оно было записано. 94.8% на Deep Memory Retrieval benchmark (vs 93.4% у MemGPT).

Граф знаний с эпизодической памятью. Episode Subgraph + Semantic Entity Subgraph + Community Subgraph. До 18.5% выше точность, в 10x меньше задержка vs MemGPT.
https://github.com/getzep/graphiti

### 7.2 mem0

> **Актуально (февраль 2026):** v1.0.3 (февраль 2026). Привлекли $24M (октябрь 2025). На 26% точнее OpenAI Memory (LOCOMO benchmark), на 91% быстрее, на 90% меньше токенов.

Слой памяти агента — контекстное восстановление данных между сессиями. Поддерживает rerankers, async-by-default, Azure OpenAI, продвинутую графовую память для сущностей.
https://mem0.ai/

### 7.3 Memori

Memory engine в одну строку: `memori.enable()`. Работает на обычной SQL базе, без векторки.
https://github.com/GibsonAI/Memori

### 7.4 Context Editing в Claude API

Агенты могут хранить данные вне окна контекста и работать с длинными задачами.
https://docs.claude.com/en/docs/build-with-claude/context-editing

---

## 8. OCR и парсинг документов

### 8.1 OCRFlux

Мультимодальный OCR на базе VLM (3B параметров), конвертирует PDF и изображения в чистый Markdown. Работает на GPU 3090. 2.5K звёзд, активно поддерживается.
https://github.com/chatdoc-com/OCRFlux

### 8.2 dots-ocr

Vision-language модель 1.7B, SOTA в мультиязычном OCR, 100+ языков.
https://github.com/rednote-hilab/dots.ocr

### 8.3 Chandra (Datalab)

Обошла dots-ocr на независимых бенчмарках, 40+ языков.
https://github.com/datalab-to/chandra

### 8.4 PaddleOCR-VL (Baidu)

> **Актуально (февраль 2026):** Вышла PaddleOCR-VL-1.5 (январь 2026) — 94.5% точности на OmniDocBench. PP-OCRv5 (май 2025) добавил +13 пунктов точности vs v4.

0.9B параметров, #1 по бенчмарку OmniBenchDoc, 100+ языков. Таблицы, формулы, рукописные заметки. Поддержка AMD ROCm GPU.
https://github.com/PaddlePaddle/PaddleOCR

### 8.5 Granite-Docling-258M (IBM)

Ультракомпактная модель для полного цикла преобразования документов.
https://huggingface.co/ibm-granite/granite-docling-258M

### 8.6 MarkItDown (Microsoft)

Конвертирует PDF, Word, Excel, PPT, HTML, JSON, XML, EPUB, изображения, аудио, ZIP, YouTube в Markdown. **86K+ звёзд.** Интегрирован с MCP для Claude Desktop.
https://github.com/microsoft/markitdown

### 8.7 Tensorlake

Вытаскивает структурированную информацию из любого неструктурированного документа. С цитированием и bounding box, готово для RAG.
https://github.com/tensorlakeai/tensorlake

---

## 9. Веб-скрейпинг и данные

### 9.1 Firecrawl v2

> **Актуально (февраль 2026):** Series A ($14.5M, август 2025). 350K+ разработчиков. Официальный MCP-сервер (firecrawl-mcp-server) для Claude и Cursor.

API для поиска, краулинга и извлечения данных. Эндпоинт `/extract` — описываешь в промпте что вытащить, получаешь структурированные данные. Новые возможности: batch-обработка тысяч URL асинхронно, отслеживание изменений на сайтах, рендеринг JavaScript/динамического контента.
https://www.firecrawl.dev/

### 9.2 GitHub URL-хаки

- Замени `hub` на `1file` в URL — все файлы репо в одном текстовом файле для LLM
- Добавь `bolt.new/` перед `github.com` — откроется в IDE Bolt с AI
- Добавь `0` к URL Pull Request — AI разберёт изменения
- Замени `github.com` на `gitmcp.io` — получишь MCP-сервер

---

## 10. Автоматизация и DevOps

### 10.1 n8n — автоматизация воркфлоу

> **Актуально (февраль 2026):** n8n 2.0+. Появились Human-in-the-Loop контролы для AI-агентов, нативная поддержка Python, интеграция с MCP для динамической смены инструментов, продвинутые системы памяти (Redis, Postgres/Supabase Vector Memory).

Локальный запуск с Ollama, 400+ интеграций, PostgreSQL.
https://github.com/n8n-io/self-hosted-ai-starter-kit

7000 готовых воркфлоу: https://n8nworkflows.xyz/

### 10.2 claude-squad — параллельные Claude Code агенты

> **Актуально (февраль 2026):** v1.0.14, 5.1K звёзд. Поддерживает Claude Code, Aider, Codex, OpenCode, Amp.

Запуск задач в фоне, управление в одном окне, изоляция каждой задачи.
https://github.com/smtg-ai/claude-squad

### 10.3 GitHub Actions + Claude Code

```
/install-github-app
```
Claude может делать ревью кода, находить баги, создавать PR асинхронно.
https://docs.anthropic.com/en/docs/claude-code/github-actions

### 10.4 VibeKit CLI — защита для кодинг-агентов

Вырезка API-ключей, мониторинг, изоляция в песочнице.
https://github.com/superagent-ai/vibekit

### 10.5 Strix — AI-хакер для CI/CD

Автономные агенты находят уязвимости и проверяют их PoC-ами. Запускается локально в Docker.
```bash
pipx install strix-agent
```
https://github.com/usestrix/strix

---

## 11. Качество кода и анализ

### 11.1 pyscn — анализ Python-кода

Проверяет AI-сгенерированный код: мёртвый/дублированный код, связность модулей, сложность функций. До 100K строк/сек.
https://github.com/ludo-technologies/pyscn

### 11.2 Gitvizz

Визуализирует репозиторий в виде интерактивного графа связей.
https://gitvizz.com

### 11.3 Google Code Wiki

Превращает любой репо в интерактивную документацию с диаграммами и навигацией.
https://codewiki.google/

---

## 12. Рекомендованные стеки

### 12.1 Стек для AI-приложения

```
Vibe coding → Cursor + Claude (Sonnet 4.5)
Auth + БД   → Supabase (с MCP-сервером для Claude/Cursor)
Фреймворк   → Next.js + AI SDK
AI-провайдер → OpenRouter AI (500+ моделей, 18 бесплатных)
Деплой       → Vercel
Платежи      → Stripe
```

### 12.2 Стек для fullstack на бесплатном тарифе

Cloudflare + Next.js шаблон с БД, хранилищем, AI-вычислениями:
https://github.com/ifindev/fullstack-next-cloudflare

### 12.3 PocketBase — бесплатный backend

Аутентификация, файлы, БД в реальном времени, панель администратора, SDK для JavaScript. По-прежнему pre-v1.0 (активная разработка, последнее обновление — февраль 2026). Не рекомендуется для критичных продакшн-систем.
https://pocketbase.io

### 12.4 Supabase — AI-интеграции (2026)

Официальный MCP-сервер для Claude/Cursor, AI-ассистент в Dashboard (функции, триггеры), векторные интеграции с OpenAI/HuggingFace, Multigres для масштабирования. Оценка $5B.
https://supabase.com

---

## 13. Обучающие ресурсы

### 13.1 Курсы

| Курс | Что внутри | Ссылка |
|------|-----------|--------|
| **Build with Claude** (Anthropic) | API, агенты, MCP, RAG, промпт-инженерия | https://www.anthropic.com/learn/build-with-claude |
| **Claude Code** (DeepLearning.ai) | Figma→код, Playwright MCP, best practices | https://deeplearning.ai/short-courses/claude-code-a-highly-agentic-coding-assistant/ |
| **MCP от Cloudflare** | Практический воркшоп, деплой в прод | https://learnmcp.examples.workers.dev |
| **MCP для начинающих** (Microsoft) | 25 модулей, Python/JS/C#/Java | https://github.com/microsoft/mcp-for-beginners |
| **AI Agents Intensive** (Kaggle) | 5-дневный интенсив по агентам | https://rsvp.withgoogle.com/events/google-ai-agents-intensive_2025 |
| **LLM от Stanford** | Трансформеры, токенизация, обучение | https://cme295.stanford.edu/syllabus/ |
| **Cursor Learn** | ~1 час, паттерны, тесты, задания | https://cursor.com/ru/learn |
| **Голосовые агенты** (Google ADK) | Реалтайм, кастомные API, память | https://deeplearning.ai/short-courses/building-live-voice-agents-with-googles-adk/ |

### 13.2 Репозитории для практики

| Репозиторий | Звёзды | Что внутри |
|-------------|--------|-----------|
| awesome-llm-apps | 14K+ | От базовых до продвинутых: MCP, RAG, мультиагенты |
| ai-engineering-hub | 24K+ | 90+ проектов по AI-агентам, RAG, MCP |
| LLMs-from-scratch | 85K+ | Код для разработки LLM с нуля (rasbt) |
| claude-cookbooks | 30K+ | Готовые примеры работы с Claude API |
| agents-towards-production | — | Туториалы по деплою агентов в прод |
| llm-engineer-toolkit | — | 120+ библиотек по этапам разработки LLM |

### 13.3 Дорожная карта AI Engineering

13K+ звёзд, 1000+ статей и репозиториев, сопровождает книгу «AI Engineering» (2025): https://github.com/chiphuyen/aie-book

### 13.4 Smol Training Playbook (Hugging Face)

200+ страниц про предобучение, постобучение и инфраструктуру LLM.
https://huggingface.co/spaces/HuggingFaceTB/smol-training-playbook

---

## 14. Полезные утилиты

| Инструмент | Для чего | Ссылка |
|-----------|---------|--------|
| **Onlook** | Figma + Cursor для веб-дизайна | https://github.com/onlook-dev/onlook |
| **ScreenCoder** | Скриншот → фронтенд-код | https://github.com/leigest519/ScreenCoder |
| **Open Lovable** | Копирует сайт в React-приложение | https://github.com/mendableai/open-lovable |
| **database.build** | AI-генерация SQL-схем + deploy в Supabase | https://database.build |
| **Conar** | AI генерирует SQL-запросы | https://github.com/wannabespace/conar |
| **Postgresus** | Автобэкапы PostgreSQL | https://github.com/RostislavDugin/postgresus |
| **ROMA** | Deep Research, open-source | https://github.com/sentient-agi/ROMA |
| **Stitch (Google)** | AI-дизайн интерфейсов + экспорт в Figma | https://stitch.withgoogle.com/ |
| **DeepSite V2** | Open-source генерация UI | https://deepsite.hf.co/projects/new |
| **Paper2Agent** | Код из научных статей → MCP-сервер | https://github.com/jmiao24/Paper2Agent |
| **Skill Seekers** | Документация → Claude Skill | https://github.com/yusufkaraaslan/Skill_Seekers |
| **aitmpl.com** | Агенты, команды, MCP одной строкой | https://aitmpl.com |

---

## 15. Безопасность и мониторинг

### 15.1 Уроки из инцидентов

**Replit удалил продакшн-базу:** AI стёр БД с тысячами записей, несмотря на запрет в конфиге. Урок: всегда делайте бэкапы, не давайте AI полный доступ к прод-данным.

**Anthropic сорвала шпионскую AI-кампанию:** Первый задокументированный случай масштабной кибератаки автономной AI-системой.
https://www.anthropic.com/news/disrupting-AI-espionage

**Chat & Ask AI Data Breach (февраль 2026):** 300M сообщений от 25M пользователей утекли из-за неправильной конфигурации Firebase. Урок: AI-приложения хранят чувствительные данные — защищайте хранилища.

**Microsoft 365 Copilot EchoLeak:** Zero-click prompt injection уязвимость. Урок: агентные системы уязвимы к инъекциям через контент, который они обрабатывают.

> **Тренд 2026:** 70% инцидентов 2025 года связаны с GenAI. Агентный AI — источник самых опасных сбоев (кража крипто, злоупотребление API). 100% руководителей по безопасности планируют внедрять агентный AI, но большинство не могут остановить «взбесившихся» агентов.

### 15.2 Инструменты безопасности

- **VibeKit** — защитный слой для кодинг-агентов (вырезка ключей, мониторинг, песочница). Публичный запуск 5 февраля 2026. Работает офлайн в Docker/Podman, MIT-лицензия. https://github.com/superagent-ai/vibekit
- **Strix** — AI-тестирование безопасности в CI/CD. Автономные агенты с автоматизацией браузера, HTTP proxy, терминал. Apache 2.0. https://github.com/usestrix/strix
- **pyscn** — анализ качества AI-сгенерированного кода (v1.1.1, продакшн-статус)
- **Claude Code prompt hooks** — PreToolUse для запрета правок в .env
- **CodeMender (Google DeepMind)** — AI-агент для безопасности кода
- **Snyk Open Source** — AI-обнаружение уязвимостей с автофиксами
