---
module: "05_agents_mcp"
lesson: 2
title: "Экосистема MCP-серверов"
type: "reference"
prerequisites: ["05_agents_mcp/lesson_01"]
difficulty: "intermediate"
tags: ["mcp", "ecosystem", "servers", "registry", "awesome-mcp"]
---

# Подмодуль 2: Экосистема MCP-серверов

## Введение

Model Context Protocol (MCP) — это не просто протокол, это целая экосистема, которая стремительно растет и развивается. По состоянию на 2025 год, сообщество разработало сотни MCP-серверов, покрывающих практически все аспекты разработки, от работы с файлами и базами данных до интеграции с облачными сервисами и специализированными инструментами.

В этом подмодуле мы разберем масштабы экосистемы MCP, изучим главные категории серверов, рассмотрим конкретные реализации и паттерны интеграции. Вы узнаете, как выбрать подходящие MCP-серверы для вашего проекта, как создать кастомный сервер и как эффективно комбинировать несколько серверов для решения сложных задач.

---

## 1. Обзор экосистемы MCP: масштаб и рост

### 1.1 Статистика и масштаб

По данным на март 2025 года, экосистема MCP содержит:

- **500+ официально задокументированных MCP-серверов** на различных платформах
- **100+ категорий использования** — от базовых файловых операций до специализированных решений для конкретных отраслей
- **Ежемесячный рост на 15-20%** новых серверов и интеграций
- **20+ языков программирования**, на которых написаны MCP-серверы (Python, TypeScript/JavaScript, Go, Rust, C#, Java и т.д.)

### 1.2 Сообщество и источники

Основные источники информации об MCP-серверах:

**Awesome MCP Servers** (https://github.com/punkpeye/awesome-mcp-servers) — главный репозиторий с кураторским списком MCP-серверов. Содержит подробное описание каждого сервера, требования к установке, примеры использования.

**Glama.ai MCP Directory** (https://glama.ai/mcp/servers) — веб-интерфейс для поиска и фильтрации MCP-серверов с возможностью тестирования прямо в браузере.

**MCP Inspector** (https://glama.ai/mcp/inspector) — инструмент для локального тестирования MCP-серверов с выводом всех доступных инструментов и их параметров.

**Официальная документация** (https://modelcontextprotocol.io/) — спецификация MCP и руководства по разработке.

### 1.3 Экосистемные игроки

В экосистеме MCP можно выделить несколько ключевых групп:

**Разработчики инструментов и IDE** — Anthropic (Claude), VS Code, Cursor, Cline создают встроенную поддержку MCP.

**Авторы серверов** — сообщество разработчиков со всего мира, создающих специализированные и общего назначения MCP-серверы.

**Провайдеры сервисов** — облачные платформы и SaaS-приложения, предоставляющие MCP-интерфейсы к своим API (GitHub, GitLab, Slack, AWS и т.д.).

**Интеграторы** — платформы и фреймворки, упрощающие подключение нескольких MCP-серверов (DeepMCPAgent, FastMCP и др.).

---

## 2. Категории MCP-серверов

MCP-серверы организованы по функциональным категориям. Рассмотрим основные из них подробно.

### 2.1 Файловые системы и облачные хранилища

Эта категория включает серверы для работы с локальными и облачными файловыми системами.

**stdio-filesystem (Anthropic)** 🎖️

Официальный MCP-сервер для работы с локальной файловой системой. Предоставляет инструменты для чтения, записи, создания и удаления файлов в указанных директориях.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/projects"]
    }
  }
}
```

Ключевые инструменты:
- `read_file` — чтение содержимого файла
- `write_file` — запись/создание файла
- `list_directory` — список файлов в директории
- `move_file` — перемещение файла
- `delete_file` — удаление файла

**S3-MCP** 📇

TypeScript-сервер для работы с AWS S3. Позволяет читать, писать и управлять объектами в S3-бакетах прямо через MCP.

```json
{
  "mcpServers": {
    "s3": {
      "command": "npx",
      "args": ["s3-mcp"],
      "env": {
        "AWS_ACCESS_KEY_ID": "YOUR_KEY",
        "AWS_SECRET_ACCESS_KEY": "YOUR_SECRET",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**Google Drive MCP** 📇 ☁️

Интеграция с Google Drive для работы с документами, таблицами и папками через MCP.

**Azure Blob Storage MCP** 📇 ☁️

Сервер для взаимодействия с Azure Blob Storage с поддержкой загрузки, скачивания и управления контейнерами.

**Dropbox MCP** 📇 ☁️

Интеграция с Dropbox для управления файлами и папками через MCP-интерфейс.

**OneDrive MCP** 📇 ☁️

Сервер для работы с Microsoft OneDrive и SharePoint.

### 2.2 Базы данных

Серверы для работы с различными СУБД, от реляционных до NoSQL.

**PostgreSQL MCP** 📇

TypeScript-сервер для работы с PostgreSQL. Позволяет выполнять SQL-запросы, управлять схемой и получать метаинформацию о БД.

```json
{
  "mcpServers": {
    "postgresql": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres"],
      "env": {
        "PG_CONNECTION_STRING": "postgresql://user:password@localhost:5432/dbname"
      }
    }
  }
}
```

Типичные инструменты:
- `query` — выполнение SQL-запроса
- `exec` — выполнение SQL-команды без возврата результатов
- `schema_info` — получение информации о схеме БД
- `table_info` — информация о конкретной таблице

**MySQL MCP** 📇

Аналог для MySQL/MariaDB. Предоставляет инструменты для работы с таблицами, выполнения запросов и управления данными.

```json
{
  "mcpServers": {
    "mysql": {
      "command": "npx",
      "args": ["mysql-mcp"],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "root",
        "MYSQL_PASSWORD": "password",
        "MYSQL_DATABASE": "mydb"
      }
    }
  }
}
```

**MongoDB MCP** 📇

Сервер для работы с MongoDB. Поддерживает запросы, вставку, обновление и удаление документов.

```json
{
  "mcpServers": {
    "mongodb": {
      "command": "npx",
      "args": ["mongodb-mcp"],
      "env": {
        "MONGODB_CONNECTION_STRING": "mongodb://localhost:27017/mydb"
      }
    }
  }
}
```

**Redis MCP** 🐍

Python-сервер для работы с Redis. Поддерживает все основные команды Redis: GET, SET, LPUSH, SADD и т.д.

```json
{
  "mcpServers": {
    "redis": {
      "command": "python",
      "args": ["-m", "redis_mcp"],
      "env": {
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

**SQLite MCP** 📇

Легковесный сервер для работы с локальными SQLite-БД. Идеален для локальной разработки и тестирования.

**DuckDB MCP** 📇

Аналитический движок, интегрированный как MCP-сервер. Отличен для работы с парке-файлами, CSV и других форматов данных.

**Elastic MCP** 📇 ☁️

Сервер для работы с Elasticsearch. Позволяет выполнять поиск, индексирование и аналитику данных.

### 2.3 Разработка и DevOps (GitHub, GitLab, Docker, Kubernetes)

**GitHub MCP** (Anthropic) 🎖️ 📇 ☁️

Официальный сервер для работы с GitHub API. Позволяет автоматизировать работу с репозиториями, issues, pull requests, workflow и т.д.

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN"
      }
    }
  }
}
```

Основные инструменты:
- `repo_search` — поиск репозиториев
- `repo_info` — информация о репозитории
- `list_issues` — список issues
- `create_issue` — создание issue
- `create_pull_request` — создание PR
- `list_pull_requests` — список PR
- `list_commits` — просмотр коммитов
- `create_workflow_dispatch` — запуск GitHub Actions

**GitLab MCP** 📇 ☁️

Аналог для GitLab. Работает с GitLab API для управления проектами, issues, merge requests и pipelines.

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "npx",
      "args": ["gitlab-mcp"],
      "env": {
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_PRIVATE_TOKEN": "YOUR_TOKEN"
      }
    }
  }
}
```

**Docker MCP** 📇 🏠

Сервер для управления Docker-контейнерами. Позволяет создавать, запускать, останавливать контейнеры и управлять образами.

```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["docker-mcp"]
    }
  }
}
```

Инструменты:
- `list_containers` — список контейнеров
- `run_container` — запуск контейнера
- `stop_container` — остановка контейнера
- `list_images` — список образов
- `build_image` — сборка Docker-образа

**Kubernetes MCP** 📇 ☁️

Сервер для управления Kubernetes-кластерами. Поддерживает развертывание, масштабирование и мониторинг приложений.

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "npx",
      "args": ["k8s-mcp"],
      "env": {
        "KUBECONFIG": "/path/to/kubeconfig"
      }
    }
  }
}
```

**Git MCP** 📇 🏠

Локальный сервер для управления Git-репозиториями. Выполняет git-команды, читает логи, управляет ветками.

**Bitbucket MCP** 📇 ☁️

Интеграция с Atlassian Bitbucket для управления репозиториями и pull requests.

**AWS MCP** 📇 ☁️

Полнофункциональный сервер для работы с AWS API. Поддерживает EC2, S3, Lambda, CloudWatch и другие сервисы.

**CI/CD Pipeline MCP** 📇

Обобщенный сервер для управления CI/CD-пайплайнами различных платформ (Jenkins, CircleCI, Travis CI).

### 2.4 Веб и браузеры (Puppeteer, Playwright, Chrome DevTools)

**Chrome DevTools MCP** 🎖️ 📇 🏠

Официальный сервер от Google для подключения Chrome DevTools к AI-агентам. Это революционное решение позволяет AI видеть и понимать то, что происходит в браузере.

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest"]
    }
  }
}
```

**Основные инструменты:**

- `performance_start_trace` — начало трассировки производительности
- `performance_stop_trace` — завершение трассировки
- `navigate` — переход на URL
- `get_page_content` — получение содержимого страницы
- `get_console_messages` — получение логов консоли
- `get_network_requests` — получение сетевых запросов
- `get_dom_info` — информация о DOM
- `inspect_element` — инспекция элемента
- `get_accessibility_tree` — дерево доступности

**Пример использования:**

```
Пользователь: "Проверь LCP на web.dev"

Chrome DevTools MCP:
1. Открывает Chrome
2. Переходит на web.dev
3. Запускает performance trace
4. Останавливает трассировку
5. Анализирует результаты
6. Возвращает метрики LCP, FCP, CLS
```

**Puppeteer MCP** 📇 🏠

Node.js-библиотека для автоматизации браузера, обернутая в MCP-сервер. Позволяет программно управлять Chrome/Chromium.

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["puppeteer-mcp"]
    }
  }
}
```

Инструменты:
- `launch_browser` — запуск браузера
- `goto` — переход на страницу
- `screenshot` — снимок экрана
- `pdf` — экспорт в PDF
- `fill_form` — заполнение форм
- `click` — клик по элементу
- `evaluate` — выполнение JavaScript

**Playwright MCP** 📇 🏠

Альтернатива Puppeteer, созданная Microsoft. Поддерживает Chrome, Firefox и Safari.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["playwright-mcp"],
      "env": {
        "BROWSER": "chromium"
      }
    }
  }
}
```

**Selenium MCP** 📇 🏠

Классический инструмент для веб-автоматизации, интегрированный как MCP-сервер.

**Web Scraper MCP** 📇 ☁️

Специализированный сервер для веб-скрейпинга с поддержкой CSS-селекторов, XPath и JavaScript-вычисления.

**OpenAI Web Search MCP** 🐍 ☁️

Сервер для выполнения веб-поиска через OpenAI's native web search API.

**Browserless.io MCP** ☁️

Облачный сервер браузерной автоматизации, предоставляющий удаленный доступ к Chrome через MCP.

### 2.5 AI и ML (Memory, Embeddings, Model Management)

**Embeddings MCP** 📇 ☁️

Сервер для работы с векторными вложениями. Позволяет преобразовывать текст в векторы для семантического поиска.

```json
{
  "mcpServers": {
    "embeddings": {
      "command": "npx",
      "args": ["embeddings-mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "EMBEDDING_MODEL": "text-embedding-3-small"
      }
    }
  }
}
```

**Memory MCP** 📇

Сервер для долговременной памяти агентов с использованием графов знаний (knowledge graphs).

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["memory-mcp"],
      "env": {
        "KNOWLEDGE_GRAPH_DB": "sqlite:///memory.db"
      }
    }
  }
}
```

Инструменты:
- `add_memory` — добавление в память
- `query_memory` — поиск по памяти
- `update_memory` — обновление записи
- `create_relationship` — создание связей между фактами
- `query_graph` — запрос к графу знаний

**VectorDB MCP** 📇

Сервер для работы с векторными базами данных (Pinecone, Weaviate, Milvus).

```json
{
  "mcpServers": {
    "vectordb": {
      "command": "npx",
      "args": ["vectordb-mcp"],
      "env": {
        "VECTORDB_API_KEY": "YOUR_API_KEY",
        "VECTORDB_INDEX": "documents"
      }
    }
  }
}
```

**RAG (Retrieval-Augmented Generation) MCP** 📇

Специализированный сервер для RAG-приложений. Позволяет индексировать документы и выполнять семантический поиск.

**LLM Router MCP** 📇

Сервер для маршрутизации запросов к различным LLM-моделям в зависимости от типа задачи.

**Model Management MCP** 📇

Сервер для управления локально развернутыми LLM-моделями (Ollama, vLLM, LM Studio).

**Hugging Face MCP** 📇 ☁️

Интеграция с Hugging Face Model Hub для загрузки и использования моделей.

### 2.6 Коммуникации (Slack, Discord, Email)

**Slack MCP** (Anthropic) 🎖️ 📇 ☁️

Официальный сервер для работы с Slack API. Позволяет отправлять сообщения, управлять каналами и получать информацию.

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-..."
      }
    }
  }
}
```

Основные инструменты:
- `send_message` — отправка сообщения в канал
- `get_channels` — список каналов
- `list_messages` — список сообщений
- `thread_message` — ответ в треде
- `update_message` — редактирование сообщения
- `get_user_info` — информация о пользователе

**Discord MCP** 📇 ☁️

Сервер для автоматизации Discord-серверов и ботов.

```json
{
  "mcpServers": {
    "discord": {
      "command": "npx",
      "args": ["discord-mcp"],
      "env": {
        "DISCORD_BOT_TOKEN": "YOUR_TOKEN"
      }
    }
  }
}
```

**Email MCP** 📇

Сервер для работы с электронной почтой. Поддерживает IMAP, SMTP и Exchange.

```json
{
  "mcpServers": {
    "email": {
      "command": "npx",
      "args": ["email-mcp"],
      "env": {
        "EMAIL_HOST": "smtp.gmail.com",
        "EMAIL_USER": "your-email@gmail.com",
        "EMAIL_PASSWORD": "app-password"
      }
    }
  }
}
```

Инструменты:
- `send_email` — отправка письма
- `read_email` — чтение письма
- `list_emails` — список писем
- `search_emails` — поиск по письмам
- `create_draft` — создание черновика

**Teams MCP** 📇 ☁️

Интеграция с Microsoft Teams для отправки сообщений и управления каналами.

**Telegram MCP** 🐍 ☁️

Сервер для создания Telegram-ботов и автоматизации.

**Twilio MCP** 📇 ☁️

Сервер для отправки SMS и звонков через Twilio API.

**Matrix/Element MCP** 📇 ☁️

Сервер для децентрализованной коммуникации через Matrix-протокол.

### 2.7 Визуализация (AntV Chart MCP)

**AntV Chart MCP Server** 📇

Специализированный MCP-сервер от Alibaba для генерации диаграмм и визуализаций через AI.

```json
{
  "mcpServers": {
    "mcp-server-chart": {
      "command": "npx",
      "args": ["-y", "@antv/mcp-server-chart"]
    }
  }
}
```

Или на Windows:

```json
{
  "mcpServers": {
    "mcp-server-chart": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@antv/mcp-server-chart"]
    }
  }
}
```

**26+ типов поддерживаемых диаграмм:**

1. **Area Chart** (`generate_area_chart`) — диаграмма с областями для отображения тренда данных
2. **Bar Chart** (`generate_bar_chart`) — горизонтальная столбчатая диаграмма
3. **Column Chart** (`generate_column_chart`) — вертикальная столбчатая диаграмма
4. **Line Chart** (`generate_line_chart`) — линейная диаграмма для временных рядов
5. **Pie Chart** (`generate_pie_chart`) — круговая диаграмма для долей
6. **Scatter Plot** (`generate_scatter_chart`) — точечная диаграмма
7. **Radar Chart** (`generate_radar_chart`) — радарная диаграмма для многомерных данных
8. **Boxplot** (`generate_boxplot_chart`) — ящик с усами для распределения
9. **Violin Chart** (`generate_violin_chart`) — скрипка для плотности распределения
10. **Histogram** (`generate_histogram_chart`) — гистограмма
11. **Dual Axes Chart** (`generate_dual_axes_chart`) — график с двумя осями Y
12. **Treemap** (`generate_treemap_chart`) — иерархическая тепловая карта
13. **Funnel Chart** (`generate_funnel_chart`) — воронка для отображения потерь данных
14. **Sankey Chart** (`generate_sankey_chart`) — диаграмма Санкея для потоков
15. **Network Graph** (`generate_network_graph`) — граф сетей и связей
16. **Heatmap** — тепловая карта (если поддерживается)
17. **Bubble Chart** — пузырьковая диаграмма (если поддерживается)
18. **Waterfall Chart** — каскадная диаграмма
19. **Word Cloud** (`generate_word_cloud_chart`) — облако слов
20. **Fishbone Diagram** (`generate_fishbone_diagram`) — диаграмма Ишикавы
21. **Mind Map** (`generate_mind_map`) — майндмап
22. **Flow Diagram** (`generate_flow_diagram`) — блок-схема
23. **Organization Chart** (`generate_organization_chart`) — организационная структура
24. **Liquid Chart** (`generate_liquid_chart`) — жидкостная диаграмма для процентов
25. **District Map** (`generate_district_map`) — географическая карта (Китай)
26. **Pin Map** (`generate_pin_map`) — карта с точками POI
27. **Path Map** (`generate_path_map`) — карта маршрутов
28. **Venn Diagram** (`generate_venn_chart`) — диаграмма Венна
29. **Spreadsheet** (`generate_spreadsheet`) — таблица и сводные таблицы

**Пример использования:**

```json
// Запрос на создание диаграммы
{
  "type": "line",
  "data": [
    { "time": "2025-01", "value": 512 },
    { "time": "2025-02", "value": 1024 },
    { "time": "2025-03", "value": 2048 }
  ],
  "xField": "time",
  "yField": "value",
  "title": "Рост активности по месяцам"
}
```

**Конфигурация с приватным развертыванием:**

```json
{
  "mcpServers": {
    "mcp-server-chart": {
      "command": "npx",
      "args": ["-y", "@antv/mcp-server-chart"],
      "env": {
        "VIS_REQUEST_SERVER": "https://your-private-server.com/api/chart",
        "SERVICE_ID": "your-service-id",
        "DISABLED_TOOLS": "generate_fishbone_diagram,generate_mind_map"
      }
    }
  }
}
```

**CLI запуск:**



**Скрипты развертывания и управления:**

Bash скрипты автоматизируют процесс установки, конфигурации и управления MCP-сервером. Типичный скрипт может: загрузить зависимости, создать необходимые директории, установить переменные окружения, запустить сервер и его зависимости.

Хорошие скрипты обеспечивают идемпотентность — результат должен быть одинаковым независимо от того, сколько раз выполнить скрипт. Это означает проверку, установлен ли пакет, прежде чем пытаться установить его, удаление старых данных перед созданием новых, и т.д.

В production среде скрипты управления обычно становятся частью систем оркестрации (systemd, supervisor, Kubernetes), которые гарантируют, что сервер всегда запущен и перезапускается при сбое.


---

## Заключение

Экосистема MCP представляет собой мощную и быстро развивающуюся платформу для интеграции AI с внешними системами. От файловых систем и баз данных до специализированных инструментов для анализа и визуализации — MCP-серверы покрывают практически все потребности современной разработки.

**Ключевые takeaway:**

1. **Масштаб** — 500+ серверов, постоянный рост
2. **Разнообразие** — от базовых до специализированных решений
3. **Chrome DevTools MCP** — революция в отладке браузера
4. **AntV Chart MCP** — 26+ типов диаграмм автоматически
5. **DeepMCPAgent** — фреймворк для мощных агентов
6. **Создание своих серверов** — просто с TypeScript или Python
7. **Интеграция** — последовательная, параллельная, иерархическая

Используя эти инструменты и паттерны, вы можете создавать sophisticated AI-агентов, которые не просто генерируют код, но и видят результаты, тестируют, отлаживают и визуализируют данные — всё как настоящий разработчик.

---

## Дополнительные ресурсы

- **Awesome MCP Servers**: https://github.com/punkpeye/awesome-mcp-servers
- **MCP Specification**: https://modelcontextprotocol.io/
- **Chrome DevTools MCP**: https://github.com/ChromeDevTools/chrome-devtools-mcp
- **AntV Chart MCP**: https://github.com/antvis/mcp-server-chart
- **DeepMCPAgent**: https://github.com/cryxnet/deepmcpagent
- **MCP Inspector**: https://glama.ai/mcp/inspector
- **Glama MCP Directory**: https://glama.ai/mcp/servers

---

**Версия документа:** 1.0
**Дата обновления:** Март 2025
**Статус:** Готово к использованию
