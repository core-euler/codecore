---
module: "10_tooling"
lesson: 1
title: "Claude Code — tips и приёмы работы"
type: "practice"
prerequisites: ["01_foundations/lesson_02"]
difficulty: "beginner"
tags: ["claude-code", "tips", "workflow", "configuration", "productivity"]
---

# Claude Code — tips и приёмы работы

Claude Code — это CLI-инструмент от Anthropic для агентского кодинга. По сути это терминальный агент, который умеет читать файлы, запускать команды, редактировать код и взаимодействовать с внешними инструментами. В этом уроке собраны практические tips и приёмы, позволяющие выжать из Claude Code максимум.

Материал организован от базовых приёмов к продвинутым — status line, голосовой ввод, multi-Claude workflow, Gemini CLI как "миньон", работа в контейнерах и ресурсы для обучения.

---

## 1. Первые шаги и essential slash commands

### 1.1. Slash commands, которые стоит знать

Внутри Claude Code доступны десятки встроенных slash commands. Введите `/` для полного списка. Вот самые важные на старте:

| Команда | Назначение |
|---------|-----------|
| `/usage` | Показать текущее потребление rate limits — сессия, неделя, по моделям |
| `/clear` | Полностью очистить контекст и начать чистую сессию |
| `/compact` | Сжать контекст, сохранив ключевые моменты |
| `/context` | Показать распределение токенов — system prompt, tools, MCP, файлы |
| `/model` | Переключить модель (Opus, Sonnet, Haiku) прямо в сессии |
| `/chrome` | Включить/выключить интеграцию с браузером Chrome |
| `/mcp` | Управление MCP-серверами |
| `/stats` | GitHub-style activity graph — ваша статистика использования |
| `/permissions` | Управление whitelist разрешённых команд |
| `/voice` | Включить push-to-talk голосовой ввод |
| `/release-notes` | Что нового в текущей версии |

**Пример `/stats`:**
```
      Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec Jan
      ··········································▒█░▓░█░▓▒▒
  Mon ·········································▒▒██▓░█▓█░█
      ·········································░▒█▒▓░█▒█▒█

  Favorite model: Opus 4.5        Total tokens: 17.6m
  Sessions: 4.1k                  Longest session: 20h 40m 45s
```

### 1.2. Управление через горячие клавиши

Основные keyboard shortcuts для повседневной работы:

| Сочетание | Действие |
|-----------|----------|
| `Esc` | Остановить Claude mid-action (контекст сохраняется) |
| `Esc + Esc` | Открыть меню rewind — восстановить код и/или разговор с любого checkpoint |
| `Shift+Tab` | Переключение режимов: Normal → Auto-Accept → Plan Mode |
| `Ctrl+S` | Stash текущий prompt (сохранить черновик, задать быстрый вопрос, вернуться) |
| `Ctrl+B` | Отправить долгую bash-команду в background |
| `Ctrl+G` | Открыть план/prompt во внешнем текстовом редакторе |
| `Ctrl+V` | Вставить изображение из clipboard (на Mac — Ctrl, не Cmd) |

**Навигация в input box (readline-совместимая):**
- `Ctrl+A` — в начало строки
- `Ctrl+E` — в конец строки
- `Ctrl+W` — удалить предыдущее слово
- `Ctrl+U` — удалить от курсора до начала строки
- `Ctrl+K` — удалить от курсора до конца строки
- `\` + Enter — новая строка в multi-line input

### 1.3. Префикс `!` для inline bash commands

Введите `!git status` или `!npm test` — команда выполнится немедленно, и результат попадёт в контекст. Это быстрее, чем просить Claude запустить команду, потому что не тратится ход агента.

### 1.4. Esc+Esc — rewind как safety net

`Esc+Esc` (или `/rewind`) открывает scrollable menu всех checkpoints. Четыре варианта восстановления:

1. **Code + conversation** — полный откат
2. **Conversation only** — откатить диалог, оставить файлы
3. **Code only** — откатить файлы, оставить диалог
4. **Summarize from checkpoint** — сжать всё после точки

Это значит: можно спокойно пробовать подход, в котором уверены на 40%. Не сработало — rewind, никакого ущерба.

> **Ограничение:** checkpoints отслеживают только file edits. Bash-операции (миграции, изменения в базе данных) не покрываются.

---

## 2. Настройка рабочего окружения

### 2.1. Terminal aliases для быстрого запуска

Добавьте в `~/.zshrc` (или `~/.bashrc`):

```bash
alias c='claude'
alias ch='claude --chrome'
alias cs='claude --dangerously-skip-permissions'
alias q='cd ~/Desktop/projects'
```

- `c` — запуск Claude Code (наиболее частый)
- `ch` — с Chrome integration
- `cs` — с пропуском всех permission prompts (осторожно!)
- `c -c` — продолжить последний разговор (`--continue`)
- `c -r` — показать список сессий для возобновления (`--resume`)

> **Предупреждение:** `--dangerously-skip-permissions` даёт Claude полный доступ к файловой системе и командной строке. Используйте только когда полностью понимаете, что Claude может сделать с вашим кодом.

### 2.2. Disable commit/PR attribution

По умолчанию Claude Code добавляет `Co-Authored-By` в commits и footer в PR. Чтобы отключить, добавьте в `~/.claude/settings.json`:

```json
{
  "attribution": {
    "commit": "",
    "pr": ""
  }
}
```

### 2.3. Настройка EDITOR для Ctrl+G

Когда вы нажимаете `Ctrl+G`, Claude открывает prompt в вашем текстовом редакторе. Настройте переменную:

```bash
export EDITOR=vim  # или nano, code, nvim
```

Или в `~/.claude/settings.json`:

```json
{
  "env": {
    "EDITOR": "vim"
  }
}
```

### 2.4. Lazy-load MCP tools для экономии контекста

MCP tool definitions загружаются в каждый разговор по умолчанию, даже если вы их не используете. Включите ленивую загрузку:

```json
{
  "env": {
    "ENABLE_TOOL_SEARCH": "true"
  }
}
```

С версии 2.1.7 это происходит автоматически, если MCP tool descriptions превышают 10% контекстного окна.

---

## 3. Status line — живая информация в терминале

### 3.1. Что такое status line

Status line — это shell-скрипт, который выполняется после каждого хода Claude. Он отображает живую информацию внизу терминала:

```
Opus 4.5 | 📁claude-code-tips | 🔀main (2 uncommitted, synced 12m ago) | ██░░░░░░░░ 18% of 200k tokens
💬 This is good. I don't think we need to change the documentation...
```

Показывает:
- Текущую модель
- Рабочую директорию
- Git branch + количество uncommitted файлов + sync status
- Visual progress bar использования контекста (цветовая кодировка)
- Последнее сообщение (чтобы помнить, о чём разговор)

### 3.2. Быстрая настройка

Самый быстрый способ — команда `/statusline` внутри Claude Code. Она спросит, что вы хотите отображать, и сгенерирует скрипт.

Поддерживаются 10 цветовых тем: orange, blue, teal, green, lavender, rose, gold, slate, cyan, gray.

### 3.3. Зачем это нужно

Status line критически важна при работе с несколькими параллельными сессиями. Вы мгновенно видите:
- Сколько контекста осталось (не нужно запускать `/context`)
- На какой ветке работаете
- Есть ли незакоммиченные изменения

---

## 4. Голосовой ввод и voice input

### 4.1. Встроенный voice mode

Claude Code имеет встроенный voice mode:

```
/voice
```

Включает push-to-talk: удерживайте Space и диктуйте. Речь транскрибируется в реальном времени в prompt. Можно смешивать голос и набор текста в одном сообщении.

**Требования:** аккаунт на claude.ai (не API key).

**Перенастройка клавиши:** в `~/.claude/keybindings.json` можно заменить Space на другую комбинацию, например `meta+k`.

### 4.2. Локальные решения для транскрипции

Для независимого от облака голосового ввода:

- **superwhisper** — коммерческое решение для macOS
- **MacWhisper** — ещё один macOS вариант
- **Super Voice Assistant** — open source, поддерживает Parakeet v2/v3

Локальные модели достаточно точны. Даже при ошибках транскрипции (например "ExcelElanishMark" вместо "exclamation mark") Claude достаточно умён, чтобы понять, что вы имели в виду.

### 4.3. Почему голос быстрее

Голосовые промпты естественно содержат больше контекста, чем текстовые. При диктовке вы:
- Объясняете background задачи
- Упоминаете ограничения
- Описываете желаемый результат подробно
- Не экономите символы

Это работает даже в шумных местах — достаточно шептать в наушники близко к микрофону.

---

## 5. Multi-Claude workflow

### 5.1. Параллельные сессии через terminal tabs

При работе с несколькими экземплярами Claude Code используйте **каскадный** подход:

1. Новая задача → новый tab справа
2. Sweep слева направо: от старых задач к новым
3. Оптимально: максимум 3-4 параллельных задачи

### 5.2. Именование и цветовая кодировка сессий

```
/rename auth-refactor
/color red
```

Доступные цвета: red, blue, green, yellow, purple, orange, pink, cyan. При 2-3 параллельных сессиях это занимает 5 секунд и спасает от ввода в не тот терминал.

### 5.3. Git worktrees для изолированных веток

```bash
claude --worktree feature-auth
```

Создаёт изолированную рабочую копию с новой веткой. Каждый worktree имеет:
- Свою сессию Claude
- Свою ветку
- Своё состояние файловой системы

Команда Claude Code сама управляет `git worktree` setup и cleanup. Рекомендация: 2-5 параллельных worktrees.

### 5.4. Один Claude пишет, другой ревьюит

Мощный паттерн: **Session A** реализует фичу, **Session B** ревьюит с чистого контекста как staff engineer. Ревьюер не знает о shortcuts реализации и challenge-ит каждый из них.

Тот же подход для TDD:
- Session A пишет тесты
- Session B пишет код, чтобы тесты прошли

### 5.5. Fork и clone разговоров

- `/fork` (или `/branch`) — форкнуть текущий разговор, попробовать другой подход, не потеряв оригинал
- `claude -c --fork-session` — форк при возобновлении

Оба пути остаются живыми — в отличие от rewind, где возвращаешься к одной точке.

### 5.6. Agent teams (experimental)

Включите через `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Затем:

> "Create an agent team with 3 teammates to refactor these modules in parallel."

Team lead распределяет работу, у каждого teammate свой context window и shared task list. Teammates могут общаться друг с другом напрямую.

**Рекомендации:**
- 3-5 teammates, 5-6 задач на каждого
- Не назначать задачи, модифицирующие одни и те же файлы
- Начинать с research и review задач, потом переходить к параллельной реализации

---

## 6. Управление контекстом

### 6.1. Контекст как "молоко" — лучше свежий и сконденсированный

Когда вы начинаете новый разговор, Claude работает лучше всего — нет accumulated complexity от предыдущего контекста. С ростом разговора performance деградирует.

**Золотые правила:**
- Новая тема → новый разговор (`/clear`)
- Если performance падает → `/clear` и переформулировать задачу
- После 2 коррекций одного и того же → начать заново с лучшим prompt

### 6.2. Proactive compaction через HANDOFF.md

Вместо автоматической компрессии — ручной handoff:

> Put the rest of the plan in HANDOFF.md. Explain what you tried, what worked, what didn't, so that the next agent with fresh context can continue from just this file.

Claude создаёт структурированный файл с прогрессом. В следующей сессии достаточно указать путь к файлу:

```
> experiments/system-prompt-extraction/HANDOFF.md
```

### 6.3. Plan Mode как альтернатива

Включите plan mode через `Shift+Tab` или `/plan`. Попросите Claude собрать весь необходимый контекст и создать comprehensive план:

> I just enabled plan mode. Bring over all of the context that you need for the next agent. The next agent will not have any other context.

После создания плана доступны опции:
1. Clear context и auto-accept
2. Auto-accept edits
3. Manually approve edits
4. Отредактировать план

### 6.4. Half-clone для сокращения контекста

Когда разговор слишком длинный, half-clone сохраняет только вторую половину — реальные сообщения остаются нетронутыми (в отличие от `/compact`, который summariz-ит).

### 6.5. Расширение контекстного окна до 1M tokens

Opus 4.6 и Sonnet 4.6 поддерживают 1M token context. Переключение:

```
/model opus[1m]
/model sonnet[1m]
```

Переменные окружения для тонкой настройки:
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` — когда срабатывает compaction
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` — пороговый процент

---

## 7. Получение output из терминала

### 7.1. Способы извлечения контента

| Метод | Описание |
|-------|----------|
| `/copy` | Копировать последний ответ Claude в clipboard как markdown |
| `pbcopy` | Попросить Claude отправить output через `pbcopy` (macOS) |
| Файл | Записать контент в файл, открыть в VS Code |
| URL | Попросить Claude открыть URL в браузере через `open` (macOS) |
| GitHub Desktop | Открыть текущий repo в GitHub Desktop |

### 7.2. Pipe output напрямую

```bash
cat error.log | claude "explain this error and suggest a fix"
npm test 2>&1 | claude "fix the failing tests"
```

### 7.3. Cmd+A / Ctrl+A — копирование с веб-страниц

Когда Claude не может получить доступ к URL (private page, Reddit, etc.), используйте Select All → Copy → Paste. Claude достаточно умён, чтобы парсить сырой текст страницы.

**Трюк с Gmail:** нажмите "Print All" для получения print preview, затем Cmd+A — все письма в thread развёрнуты.

---

## 8. Gemini CLI как "миньон" Claude Code

### 8.1. Зачем нужен Gemini CLI

WebFetch в Claude Code не может получить доступ к некоторым сайтам (например, Reddit). Gemini CLI имеет web access и может fetches контент с сайтов, недоступных Claude напрямую.

### 8.2. Как это работает

Создайте skill в `~/.claude/skills/reddit-fetch/SKILL.md`, который использует tmux-паттерн:

1. Claude Code запускает tmux session
2. В tmux session отправляет команды в Gemini CLI
3. Gemini CLI fetches контент с недоступного сайта
4. Claude Code получает результат через `tmux capture-pane`

Skills более token-efficient, чем CLAUDE.md, потому что загружаются только при необходимости.

### 8.3. Multi-model orchestration

Можно пойти дальше и запускать разные AI CLI в контейнерах — Codex, Gemini CLI и другие. Claude Code становится центральным интерфейсом, который координирует всё: запускает модели, передаёт данные между контейнерами и хостом.

---

## 9. Claude Code в контейнерах

### 9.1. Зачем запускать в контейнере

Контейнер даёт:
- **Полную изоляцию** — если что-то пойдёт не так, повреждения ограничены контейнером
- **Лёгкий rollback** — пересоздание контейнера восстанавливает чистое состояние
- **Безопасный `--dangerously-skip-permissions`** — полная автономия без рисков

### 9.2. Когда использовать контейнеры

- Research и experimentation с неизвестными инструментами
- Long-running задачи (ночные миграции, experimental refactors)
- Обновление patches для новых версий Claude Code
- Reddit research через Gemini CLI (Tip 8)
- Любая работа, где вы хотите дать Claude полную свободу

### 9.3. Оркестрация worker Claude Code в контейнере

Архитектура:

1. Локальный Claude Code запускает tmux session
2. В tmux session запускает или подключается к контейнеру
3. Внутри контейнера Claude Code работает с `--dangerously-skip-permissions`
4. Внешний Claude Code использует `tmux send-keys` для отправки промптов и `capture-pane` для чтения output

Результат: полностью автономный "worker" Claude Code в sandbox-среде.

### 9.4. SafeClaw — удобный запуск контейнерных сессий

[SafeClaw](https://github.com/ykdojo/safeclaw) — инструмент для запуска containerized Claude Code sessions. Позволяет:
- Создавать множество изолированных сессий
- Web terminal для каждой сессии
- Централизованное управление через dashboard

---

## 10. Slim down system prompt

### 10.1. Проблема: system prompt занимает ~10% контекста

System prompt и tool definitions Claude Code занимают ~19k tokens (~10% от 200k контекста) ещё до начала работы:

| Компонент | До оптимизации | После | Экономия |
|-----------|---------------|-------|----------|
| System prompt | 3.0k | 1.8k | 1,200 tokens |
| System tools | 15.6k | 7.4k | 8,200 tokens |
| **Итого** | **~19k** | **~9k** | **~10k tokens (~50%)** |

### 10.2. Подход через patching

Patches обрезают verbose examples и redundant text из minified CLI bundle, сохраняя essential instructions. Ощущения: более "сырой", мощный инструмент, менее регулируемый (короче system instruction).

**Важно:** при использовании patches отключите auto-updates:

```json
{
  "env": {
    "DISABLE_AUTOUPDATER": "1"
  }
}
```

### 10.3. Альтернативные подходы

- `--system-prompt` или `--system-prompt-file` — упрощённый system prompt из файла
- `ENABLE_TOOL_SEARCH` — ленивая загрузка MCP tools (см. раздел 2.4)

---

## 11. Полезные навыки и паттерны работы

### 11.1. Git и GitHub CLI как профессионал

Просто попросите Claude Code выполнять Git-операции: commits (без ручного написания commit messages), branching, pulling, pushing.

**Рекомендация:** автоматически разрешайте pull, но не push — push рискованнее, если что-то пошло не так.

Для GitHub CLI (`gh`):
- Создание draft PRs — Claude Code готовит PR, вы review-ите перед marking ready
- `gh` поддерживает произвольные GraphQL запросы

```bash
# Пример: найти историю редактирования PR description
gh api graphql -f query='
  query {
    repository(owner: "...", name: "...") {
      pullRequest(number: ...) {
        userContentEdits(first: 100) {
          nodes { editedAt editor { login } }
        }
      }
    }
  }'
```

### 11.2. Claude Code как research tool

Claude Code — эффективная замена deep research:
- Исследование GitHub Actions failures через `gh` CLI
- Sentiment analysis на Reddit (через Gemini CLI)
- Exploration кодовой базы
- Научный поиск через специализированные plugins

### 11.3. Claude Code как DevOps engineer

При CI failures:

> Dig into this issue, try to find the root cause.

Claude Code анализирует логи, ищет конкретный commit или PR, определяет flaky tests. Для автоматизации — skill `/gha <url>`, который расследует GitHub Actions failures.

### 11.4. Interactive PR reviews

Не просите one-shot review. Ведите диалог:

> Walk me through the riskiest change in this PR.
> What would break if this runs concurrently?
> Is the error handling consistent with the rest of the codebase?

Conversational reviews ловят больше проблем, потому что вы drilling into areas that matter. One-shot reviews обычно флагают style nits и часто пропускают архитектурные проблемы.

### 11.5. Manual exponential backoff для долгих jobs

При ожидании Docker builds или GitHub CI:

> Check the status with increasing sleep intervals — 1 min, then 2 min, then 4 min.

Для GitHub CI: `gh run view <run-id> | grep <job-name>` экономит токены по сравнению с `gh run watch`, который выводит много строк.

### 11.6. Let Claude interview you

Когда не можете полностью специфицировать фичу:

```markdown
I want to build [brief description]. Interview me in detail
using the AskUserQuestion tool. Ask about technical implementation,
edge cases, concerns, and tradeoffs. Don't ask obvious questions.
Keep interviewing until we've covered everything,
then write a complete spec to SPEC.md.
```

Затем — fresh session с чистым контекстом и готовым spec.

### 11.7. Fan-out с `claude -p` для batch operations

```bash
for file in $(cat files-to-migrate.txt); do
  claude -p "Migrate $file from class components to hooks" \
    --allowedTools "Edit,Bash(git commit *)" &
done
wait
```

Non-interactive mode для CI, pre-commit hooks или любых скриптов. `--output-format json` для structured output.

---

## 12. Проверка и верификация output

### 12.1. Write-test cycle для автономных задач

Чтобы Claude Code мог работать автономно, ему нужен feedback loop: написать код → запустить → проверить → повторить.

**Для interactive terminals используйте tmux:**

```bash
tmux kill-session -t test-session 2>/dev/null
tmux new-session -d -s test-session
tmux send-keys -t test-session 'claude' Enter
sleep 2
tmux send-keys -t test-session '/context' Enter
sleep 1
tmux capture-pane -t test-session -p
```

### 12.2. Creative testing strategies

- **Playwright MCP** — для browser testing (accessibility tree, structured data)
- **Chrome native integration** (`/chrome`) — для визуальных задач, screenshot-based clicking
- **Visual Git client** (GitHub Desktop) — для quick review изменений
- **Draft PRs** — low-risk способ проверить changes

**Рекомендация в CLAUDE.md для Chrome:**

```markdown
# Claude for Chrome
- Use `read_page` to get element refs from the accessibility tree
- Use `find` to locate elements by description
- Click/interact using `ref`, not coordinates
- NEVER take screenshots unless explicitly requested
```

### 12.3. Double-check pattern

> Double check everything, every single claim in what you produced.
> At the end make a table of what you were able to verify.

Claude перепроверяет каждое утверждение и создаёт таблицу верификации.

---

## 13. Ресурсы для обучения

### 13.1. Официальное обучение от Anthropic

**Claude Code in Action** (Anthropic Academy / Skilljar) — курс для начинающих:
- 15 лекций, ~1 час видео + квиз
- От базового уровня (настройка, контекст) до среднего (MCP, GitHub integration, hooks)
- Сертификат по завершении

### 13.2. PSB Framework: Plan → Setup → Build

Видеоурок (~30 мин) по правильному старту проекта:
1. **Plan** — формулировка задачи и плана работ
2. **Setup** — подготовка окружения, правил, контекста (CLAUDE.md, инструкции, code style)
3. **Build** — пошаговая реализация фич, фиксация результата, проверка

### 13.3. Deep guide по Claude Code 2.0 + context engineering

Гайд от sankalp (bearblog):
- Workflow "plan → execute" и правильный старт проекта
- Команды, шорткаты, кастомные команды
- Sub-agents (Explore/read-only) — разделение задач и разгрузка контекста
- Context engineering — экономия токенов и ускорение работы

### 13.4. Community-подборки и каталоги

- **Awesome Claude** (awesomeclaude.ai) — community-подборка ссылок на доки, интеграции, гайды
- **System prompts Claude Code** — репозиторий с частями системного промпта Claude Code + token count + история изменений по версиям
- **tweakcc** CLI — кастомизация частей системного промпта
- **SkillsMP** (skillsmp.com) — каталог 33k+ скиллов для Claude Code и OpenAI Codex

### 13.5. Лучшие практики от Anthropic

[Официальный гайд с лучшими практиками](https://www.anthropic.com/engineering/claude-code-best-practices) для агентского кодирования:
- Оформление CLAUDE.md
- Выстраивание workflow
- Экономия контекста
- Ускорение итераций

### 13.6. Готовые коллекции агентов и MCP

Более 100 готовых суб-агентов, команд и MCP-плагинов для Claude Code — от ревью кода до DevOps рутины и генерации документации.

---

## 14. Персонализация и автоматизация

### 14.1. Customization spinner verbs

Пока Claude "думает", в терминале крутится spinner с глаголами вроде "Flibbertigibbeting..." и "Flummoxing...". Их можно заменить:

> Replace my spinner verbs in user settings with these: Hallucinating responsibly, Pretending to think, Confidently guessing, Blaming the context window

Или просто задайте vibe: "Replace my spinner verbs with Harry Potter spells." Claude сгенерирует список.

### 14.2. Output style configuration

```
/config
```

Встроенные стили:
- **Explanatory** — детальный, step-by-step
- **Concise** — краткий, action-focused
- **Technical** — точный, с жаргоном

Кастомные стили создаются как файлы в `~/.claude/output-styles/`.

### 14.3. Search conversation history

История хранится локально в `~/.claude/projects/`. Пути кодируются через дефисы:

```
~/.claude/projects/-Users-yk-Desktop-projects-claude-code-tips/
```

Каждый разговор — `.jsonl` файл. Поиск:

```bash
grep -l -i "keyword" ~/.claude/projects/-Users-yk-*/*.jsonl
```

Или просто спросите Claude Code: "What did we talk about regarding X today?"

### 14.4. Аудит approved commands

Инструмент `cc-safe` сканирует `.claude/settings.json` на рискованные approved commands:

```bash
npx cc-safe .
```

Обнаруживает паттерны: `sudo`, `rm -rf`, `Bash`, `chmod 777`, `curl | sh`, `git reset --hard`, `npm publish`, `docker run --privileged`.

### 14.5. DX plugin — набор полезных skills

Plugin `dx` объединяет многие инструменты:

| Skill | Описание |
|-------|----------|
| `/dx:gha <url>` | Анализ GitHub Actions failures |
| `/dx:handoff` | Создание handoff documents для continuity |
| `/dx:clone` | Clone разговоров для branching |
| `/dx:half-clone` | Half-clone для сокращения контекста |
| `/dx:reddit-fetch` | Fetch Reddit через Gemini CLI |
| `/dx:review-claudemd` | Review разговоров для улучшения CLAUDE.md |

Установка:

```bash
claude plugin marketplace add ykdojo/claude-code-tips
claude plugin install dx@ykdojo
```

---

## 15. Философия работы с Claude Code

### 15.1. Правильный уровень абстракции

Работа с Claude Code — это не бинарный выбор между "vibe coding" и "проверять каждую строку". Это спектр:

- **Vibe coding** — подходит для one-time проектов, некритичных частей
- **File structure level** — общая архитектура и организация
- **Function level** — отдельные функции и их контракты
- **Line level** — конкретные строки кода, зависимости
- **Dependency level** — глубокий аудит зависимостей

Выбирайте уровень в зависимости от критичности задачи.

### 15.2. Ваши engineering skills всё ещё важны

Problem-solving и software engineering навыки остаются крайне релевантными. Claude Code — усилитель, не замена. Знание инструментов (git bisect, tmux), паттернов (TDD, iterative development) и архитектурных принципов делает работу с Claude Code кратно эффективнее.

### 15.3. Billion token rule

Вместо правила 10,000 часов — **billion token rule**: если хотите развить хорошую интуицию для работы с AI, лучший способ — потреблять много токенов. Используйте Claude Code как можно больше, экспериментируйте, пробуйте разные подходы.

### 15.4. Automation of automation

Ищите повторяющиеся паттерны и автоматизируйте их:

1. Повторяете одно и то же Claude Code → добавьте в CLAUDE.md
2. Запускаете одни и те же команды → создайте skills
3. Одинаковый процесс каждый раз → напишите скрипт
4. Typing слишком медленный → голосовой ввод
5. Контекст переполняется → handoff documents

---

## Резюме

Не нужно применять все tips сразу. Выберите один, который решает самую раздражающую проблему из вашей последней сессии, и попробуйте завтра. Один tip, который прижился, стоит больше, чем пятьдесят в закладках.

**Ключевые takeaways:**

1. **Status line** — настройте для мониторинга контекста и git status
2. **Voice input** — используйте для более богатых промптов
3. **Multi-Claude** — worktrees + tabs + naming для параллельной работы
4. **Context management** — /clear между задачами, HANDOFF.md для continuity
5. **Gemini CLI** — как fallback для blocked sites
6. **Containers** — для рискованных и long-running задач
7. **Verify everything** — write-test cycle, draft PRs, double-check pattern
