---
module: "10_tooling"
lesson: 2
title: "50 лучших практик Claude Code"
type: "reference"
prerequisites: ["10_tooling/lesson_01"]
difficulty: "intermediate"
tags: ["best-practices", "claude-code", "prompting", "workflow"]
---

# 50 лучших практик Claude Code

Этот урок — справочник лучших практик работы с Claude Code, собранных из официальной документации Anthropic, рекомендаций Boris Cherny (создателя Claude Code), community-опыта и ежедневного использования. Практики организованы по темам: от настройки проекта и промптинга до продвинутых workflow и safety patterns.

Источник: 50 Claude Code Best Practices (Builder.io), основанный на год+ ежедневного использования.

---

## Часть 1: Настройка проекта и окружения

### Практика 1. Alias `cc` для быстрого запуска

```bash
alias cc='claude --dangerously-skip-permissions'
```

Добавьте в `~/.zshrc` или `~/.bashrc`, затем `source ~/.zshrc`. Вместо `claude` вы набираете `cc` и пропускаете все permission prompts.

> **Предупреждение:** Флаг `--dangerously-skip-permissions` намеренно пугающий. Используйте только после полного понимания того, что Claude Code может и будет делать с вашей кодовой базой.

### Практика 2. LSP-плагин для вашего языка — highest-impact plugin

LSP-плагины дают Claude автоматическую диагностику после каждого редактирования файла: type errors, unused imports, missing return types. Claude видит и исправляет проблемы до того, как вы их заметите.

```bash
# Выберите свой язык:
/plugin install typescript-lsp@claude-plugins-official
/plugin install pyright-lsp@claude-plugins-official
/plugin install rust-analyzer-lsp@claude-plugins-official
/plugin install gopls-lsp@claude-plugins-official
```

Доступны также плагины для C#, Java, Kotlin, Swift, PHP, Lua, C/C++. Откройте `/plugin` → вкладка Discover.

### Практика 3. `gh` CLI вместо MCP-сервера для GitHub

`gh` CLI обрабатывает PRs, issues и comments без отдельного MCP-сервера. CLI-инструменты более context-efficient, чем MCP-серверы, потому что не загружают tool schemas в контекстное окно. То же относится к `jq`, `curl` и другим стандартным CLI.

**Для незнакомых Claude CLI-инструментов:**

> Use 'sentry-cli --help' to learn about it, then use it to find the most recent error in production.

Claude прочитает help output, разберётся в синтаксисе и выполнит команды. Работает даже для внутренних CLI.

### Практика 4. Правильный выбор MCP-серверов

Серверы, с которых стоит начать:
- **Playwright** — browser testing и UI verification
- **PostgreSQL/MySQL** — прямые schema queries
- **Slack** — чтение bug reports и thread context
- **Figma** — design-to-code workflows

Claude Code поддерживает dynamic tool loading — серверы загружают definitions только когда Claude их требует.

### Практика 5. /init, затем вдвое сократить результат

`/init` генерирует стартовую версию CLAUDE.md на основе структуры проекта: build commands, test scripts, directory layout.

**Проблема:** output обычно раздут. Правило: если не можете объяснить, зачем строка там — удалите. Обрежьте шум, добавьте то, что отсутствует.

### Практика 6. Контекстное окно до 1M tokens

Opus 4.6 и Sonnet 4.6 поддерживают 1M token context. На Max, Team и Enterprise планах Opus автоматически получает 1M.

```
/model opus[1m]
/model sonnet[1m]
```

Переменные для тонкой настройки:
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` — порог срабатывания compaction
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` — процентный порог

---

## Часть 2: CLAUDE.md — контракт с агентом

### Практика 7. Litmus test для каждой строки CLAUDE.md

Для каждой строки в CLAUDE.md задайте вопрос: **"Допустит ли Claude ошибку без этой строки?"**

Если Claude уже делает что-то правильно сам — инструкция это шум. Каждая ненужная строка разбавляет важные.

**Бюджет:** примерно 150-200 инструкций до падения compliance. System prompt уже использует ~50 из них.

### Практика 8. После ошибки — "Update your CLAUDE.md"

Когда Claude совершает ошибку:

> Update the CLAUDE.md file so this doesn't happen again.

Claude напишет своё собственное правило. В следующей сессии он автоматически будет ему следовать.

Со временем CLAUDE.md становится living document, сформированным реальными ошибками. Чтобы файл не разрастался бесконечно, используйте `@imports` (Практика 12) для вынесения деталей в отдельные файлы.

### Практика 9. `.claude/rules/` для conditional rules

Поместите markdown-файлы в `.claude/rules/` для организации инструкций по темам. По умолчанию все rule files загружаются при старте сессии. Чтобы правило загружалось только для определённых файлов, добавьте frontmatter:

```yaml
---
paths:
  - "**/*.ts"
---
# TypeScript conventions
Prefer interfaces over types.
```

TypeScript rules загружаются при работе с `.ts` файлами, Go rules — при `.go` файлах. Claude никогда не читает конвенции языков, с которыми не работает.

### Практика 10. CLAUDE.md для suggestions, hooks для requirements

| | CLAUDE.md | Hooks |
|---|---|---|
| Compliance | ~80% | 100% |
| Характер | Advisory | Deterministic |
| Применение | Guidance, conventions | Formatting, linting, security checks |

Если что-то должно выполняться каждый раз без исключений — сделайте hook. Если это guidance — CLAUDE.md достаточно.

### Практика 11. Skills для on-demand knowledge

Skills — markdown файлы, расширяющие знания Claude по запросу. В отличие от CLAUDE.md (загружается каждую сессию), skills загружаются только при релевантности текущей задачи.

```
.claude/skills/
```

Используйте для: API conventions, deployment procedures, coding patterns, которые нужны иногда, но не всегда.

### Практика 12. @imports для lean CLAUDE.md

Ссылайтесь на документы через `@`:

```markdown
@docs/git-instructions.md
@README.md
@package.json
@~/.claude/my-project-instructions.md
```

Claude прочитает файл, когда он понадобится. `@imports` — это "вот дополнительный контекст, если нужен" без раздувания файла, который Claude читает каждую сессию.

---

## Часть 3: Prompting и взаимодействие

### Практика 13. Дайте Claude способ проверить свою работу

Включайте test commands, linter checks или expected outputs в prompt:

```markdown
Refactor the auth middleware to use JWT instead of session tokens.
Run the existing test suite after making changes.
Fix any failures before calling it done.
```

Claude запускает тесты, видит failures и фиксит без вашего участия. По словам Boris Cherny, **одно это даёт 2-3x improvement в качестве**.

Для UI changes: настройте Playwright MCP server, чтобы Claude мог открыть браузер, взаимодействовать со страницей и verify UI.

### Практика 14. "ultrathink" для complex reasoning

Ключевое слово `ultrathink` включает high effort и triggers adaptive reasoning на Opus 4.6. Claude динамически распределяет thinking в зависимости от сложности.

**Когда использовать:**
- Architecture decisions
- Tricky debugging
- Multi-step reasoning
- Всё, где нужно подумать перед действием

**Для менее сложных задач:** `/effort` для перманентной установки уровня. Нет смысла тратить thinking tokens на переименование переменной.

### Практика 15. Не интерпретируйте баги для Claude — paste raw data

Описывать баг словами медленно. Claude угадывает, вы поправляете, повторяется.

**Правильно:** вставьте error log, CI output или Slack thread напрямую и скажите "fix."

```bash
cat error.log | claude "explain this error and suggest a fix"
npm test 2>&1 | claude "fix the failing tests"
```

Ваша интерпретация добавляет абстракцию, которая часто теряет детали, необходимые Claude для точного определения root cause.

**CI pattern:** "Go fix the failing CI tests" с paste CI output — один из самых надёжных паттернов.

### Практика 16. Указывайте Claude точные файлы

Используйте `@` для ссылки на файлы:

> @src/auth/middleware.ts has the session handling.

`@` prefix резолвится в file path автоматически. Claude может grep и search самостоятельно, но каждый шаг поиска стоит токенов. Указание файлов сразу пропускает этот процесс.

### Практика 17. Vague prompts для exploration

> What would you improve in this file?

Не каждый prompt должен быть специфичным. Для onboarding в незнакомый repo — vague question даёт Claude пространство для обнаружения того, о чём вы бы не подумали спросить.

### Практика 18. После 2 corrections — начните заново

Когда вы с Claude идёте по rabbit hole коррекций, а проблема не решена — контекст заполнен failed approaches, которые активно вредят следующей попытке.

**Решение:** `/clear` и написать better starting prompt с учётом полученных знаний. Чистая сессия с sharper prompt почти всегда побеждает длинную сессию с accumulated dead ends.

### Практика 19. Let Claude interview you

Когда у вас есть идея, но не хватает деталей:

```markdown
I want to build [brief description]. Interview me in detail
using the AskUserQuestion tool. Ask about technical implementation,
edge cases, concerns, and tradeoffs. Don't ask obvious questions.
Keep interviewing until we've covered everything,
then write a complete spec to SPEC.md.
```

Когда spec готов — fresh session с чистым контекстом для реализации.

### Практика 20. Explore unfamiliar code с vague prompts

При onboarding в незнакомый repo:

> What would you improve in this file?

Claude обнаруживает patterns, inconsistencies и improvement opportunities, которые вы бы пропустили при первом чтении.

---

## Часть 4: Workflow и управление сессиями

### Практика 21. /clear между несвязанными задачами

Чистая сессия с sharp prompt побеждает messy three-hour session. Другая задача? `/clear` сначала.

Сессии деградируют, потому что accumulated context from earlier work заглушает текущие инструкции. 5 секунд на `/clear` и focused starting prompt экономят 30 минут diminishing returns.

### Практика 22. Plan Mode для неясных подходов

Plan Mode для: multi-file changes, unfamiliar code, architectural decisions. Overhead реален (несколько лишних минут), но предотвращает 20 минут уверенного решения не той проблемы.

**Пропустите** для small, clear-scope задач. Если можете описать diff в одном предложении — делайте напрямую.

`Shift+Tab` для переключения: Normal → Auto-Accept → Plan.

### Практика 23. Edit plans через Ctrl+G

Когда Claude представляет план, `Ctrl+G` открывает его в текстовом редакторе. Добавьте ограничения, удалите шаги, перенаправьте подход — до того, как Claude напишет код.

### Практика 24. /btw для quick side questions

`/btw` открывает overlay для быстрого вопроса, не загрязняя conversation history:

> Why did you choose this approach?
> What's the tradeoff with the other option?

Ответ показывается в dismissible overlay, основной контекст остаётся lean.

### Практика 25. Ctrl+S — stash prompt

В середине длинного prompt нужен быстрый ответ? `Ctrl+S` сохраняет черновик. Задайте вопрос, отправьте — черновик восстанавливается автоматически.

### Практика 26. Ctrl+B — background long-running tasks

Когда Claude запускает долгую bash-команду (test suite, build, migration):
- `Ctrl+B` отправляет в background
- Claude продолжает работать
- Вы продолжаете chatting
- Результат появляется, когда процесс завершается

### Практика 27. /loop для recurring checks

```
/loop 5m check if the deploy succeeded and report back
```

Recurring prompt в background. Поддерживает s, m, h, d. Задачи session-scoped, expire через 3 дня.

**Используйте для:** мониторинга deploys, watching CI pipelines, polling external services.

### Практика 28. --worktree для parallel branches

```bash
claude --worktree feature-auth
```

Команда Claude Code называет это "one of the biggest productivity unlocks". 3-5 worktrees, каждый со своей сессией, веткой и файловой системой.

### Практика 29. /branch для альтернативных подходов

`/branch` (или `/fork`) создаёт copy разговора в текущей точке. Попробуйте рискованный refactor в branch. Работает — оставьте. Не работает — original conversation нетронут.

Отличие от rewind: оба пути остаются живыми.

### Практика 30. Один Claude пишет, другой ревьюит

First Claude реализует фичу, second Claude ревьюит из fresh context как staff engineer. Ревьюер не знает shortcuts реализации и challenge-ит каждый.

TDD-вариант: Session A пишет тесты, Session B пишет код.

### Практика 31. Naming и color-coding сессий

```
/rename auth-refactor
/color red
```

Цвета: red, blue, green, yellow, purple, orange, pink, cyan. При 2-3 параллельных сессиях — 5 секунд усилий, спасающие от ввода в неправильный терминал.

---

## Часть 5: Контекст и compaction

### Практика 32. Guide compaction с инструкциями

При compaction (автоматически или `/compact`), укажите, что сохранить:

> /compact focus on the API changes and the list of modified files.

Добавьте standing instructions в CLAUDE.md:

```markdown
When compacting, preserve the full list of modified files and current test status.
```

### Практика 33. Subagents для чистого контекста

> Use subagents to figure out how the payment flow handles failed transactions.

Subagent — отдельный Claude instance с собственным context window. Читает файлы, анализирует, возвращает concise summary.

Main session остаётся чистой. Deep investigation может потребить половину контекста до написания кода — subagents выносят эту стоимость.

**Встроенные типы:**
- **Explore** — Haiku, fast file search
- **Plan** — read-only analysis

### Практика 34. Custom subagents для recurring tasks

В отличие от ad-hoc subagents, custom subagents — pre-configured agents в `.claude/agents/`:
- Security-reviewer agent с Opus и read-only tools
- Quick-search agent с Haiku для скорости

`/agents` для browse и создания. `isolation: worktree` для агентов с собственной файловой системой.

### Практика 35. Agent teams для multi-session coordination

Experimental. Включите `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.

> Create an agent team with 3 teammates to refactor these modules in parallel.

Team lead распределяет работу. Каждый teammate имеет свой context window и shared task list. Teammates могут общаться напрямую.

**Правила:**
- 3-5 teammates, 5-6 задач каждому
- Не модифицировать одни и те же файлы двумя teammates
- Начинать с research/review, потом parallel implementation

---

## Часть 6: Hooks — детерминированная автоматизация

### Практика 36. Auto-format через PostToolUse hook

Каждый раз, когда Claude edit-ит файл, formatter должен запускаться автоматически:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$CLAUDE_FILE_PATH\" 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

`|| true` предотвращает блокировку Claude при ошибках hook.

> **Совет:** отключите format-on-save в IDE, пока Claude работает. Сохранения редактора могут инвалидировать prompt cache.

### Практика 37. Block destructive commands через PreToolUse hook

Блокируйте `rm -rf`, `drop table`, `truncate`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "type": "command",
        "command": "if echo \"$TOOL_INPUT\" | grep -qE 'rm -rf|drop table|truncate'; then echo 'BLOCKED: destructive command' >&2; exit 2; fi"
      }
    ]
  }
}
```

Hook срабатывает до выполнения tool — destructive commands перехватываются до нанесения ущерба.

### Практика 38. Preserve context across compaction через hooks

Notification hook с compact matcher автоматически re-inject-ит ключевой контекст при каждой компрессии.

> Set up a Notification hook that after compaction reminds you of the current task, modified files, and any constraints.

**Кандидаты для re-injection:**
- Текущее описание задачи
- Список модифицированных файлов
- Hard constraints ("don't modify migration files")

Наиболее ценно для multi-hour sessions.

### Практика 39. Sound notification через Stop hook

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/afplay /System/Library/Sounds/Glass.aiff"
          }
        ]
      }
    ]
  }
}
```

Запустите задачу, переключитесь на другое — ping когда Claude закончит.

---

## Часть 7: Safety и verification

### Практика 40. /sandbox для изолированной работы

`/sandbox` включает OS-level isolation:
- Запись ограничена project directory
- Network requests лимитированы approved domains
- Seatbelt на macOS, bubblewrap на Linux

В auto-allow mode sandboxed commands выполняются без permission prompts — near-full autonomy с guardrails.

**Для unsupervised work** (overnight migrations, experimental refactors) — Docker container для полной изоляции.

### Практика 41. Allowlist safe commands через /permissions

```
/permissions
```

Перестаньте кликать "approve" на `npm run lint` в сотый раз. Добавьте trusted commands в whitelist — flow не прерывается. Для нового — всё ещё будет prompt.

### Практика 42. Always manually review критические области

Независимо от качества остального кода, **всегда ревьюйте вручную:**

| Область | Почему |
|---------|--------|
| Auth flows | Неправильный auth scope может дать несанкционированный доступ |
| Payment logic | Misconfigured webhook может стоить денег |
| Data mutations | DROP COLUMN без warning теряет данные безвозвратно |
| Destructive DB operations | Каскадные удаления могут уничтожить связанные записи |

Никакие automated tests не покрывают 100% таких сценариев.

### Практика 43. Conversational PR reviews вместо one-shot

Не просите Claude дать одноразовый review. Откройте PR в сессии и ведите разговор:

> Walk me through the riskiest change in this PR.
> What would break if this runs concurrently?
> Is the error handling consistent with the rest of the codebase?

Conversational reviews ловят больше issues, потому что вы drilling into areas that matter. One-shot reviews обычно flag-ают style nits и пропускают architectural problems.

### Практика 44. Fan-out с `claude -p` для batch operations

```bash
for file in $(cat files-to-migrate.txt); do
  claude -p "Migrate $file from class components to hooks" \
    --allowedTools "Edit,Bash(git commit *)" &
done
wait
```

Non-interactive mode. `--allowedTools` ограничивает, что Claude может делать с каждым файлом. Параллельное выполнение через `&`.

---

## Часть 8: Advanced configuration

### Практика 45. Voice dictation для richer prompts

```
/voice
```

Push-to-talk: удерживайте Space, диктуйте. Speech транскрибируется live в prompt. Голос + набор текста в одном сообщении.

Spoken prompts содержат больше контекста — при диктовке вы объясняете background, constraints, desired outcome без экономии keystrokes.

**Rebind push-to-talk key:** `~/.claude/keybindings.json` → `meta+k`.

### Практика 46. Remote control с телефона

```bash
claude remote-control
```

Подключитесь с `claude.ai/code` или Claude app на iOS/Android. Session работает локально на вашей машине — телефон/браузер это просто window.

С `--dangerously-skip-permissions`: kick off задачу → уйдите → check in с телефона когда Claude завершит.

### Практика 47. Output style configuration

```
/config
```

Встроенные стили:
- **Explanatory** — детальный, step-by-step
- **Concise** — краткий, action-focused
- **Technical** — точный, jargon-friendly

Custom styles создаются в `~/.claude/output-styles/`.

### Практика 48. Live status line

`/statusline` — настройка status line внизу терминала. Показывает: model, directory, git branch, context usage с color coding.

Критически важна при нескольких параллельных сессиях.

### Практика 49. Context window management

```
/context   # Inspect token consumption
/clear     # Reset session
/compact   # Compress while retaining key points
/memory    # Confirm loaded CLAUDE.md
```

**Проактивное управление** всегда лучше, чем ожидание автоматической компрессии.

### Практика 50. Customize spinner verbs

> Replace my spinner verbs with these: Hallucinating responsibly, Pretending to think, Confidently guessing, Blaming the context window

Или задайте vibe:

> Replace my spinner verbs with Harry Potter spells.

Claude сгенерирует список. Маленькая вещь, которая делает ожидание приятнее.

---

## Сводная таблица: практики по категориям

### Настройка проекта (Practices 1-6)

| # | Практика | Impact |
|---|----------|--------|
| 1 | Alias `cc` | Ускоряет запуск каждой сессии |
| 2 | LSP plugin | Highest-impact plugin — автоматическая диагностика |
| 3 | `gh` CLI | Context-efficient работа с GitHub |
| 4 | MCP servers | Playwright, PostgreSQL, Slack, Figma |
| 5 | /init + cut in half | Стартовый CLAUDE.md без bloat |
| 6 | 1M context | Больше пространства для работы |

### CLAUDE.md (Practices 7-12)

| # | Практика | Impact |
|---|----------|--------|
| 7 | Litmus test | Каждая строка оправдана |
| 8 | Update after mistakes | Living document |
| 9 | .claude/rules/ | Conditional loading |
| 10 | CLAUDE.md vs hooks | Advisory vs deterministic |
| 11 | Skills | On-demand knowledge |
| 12 | @imports | Lean main file |

### Prompting (Practices 13-20)

| # | Практика | Impact |
|---|----------|--------|
| 13 | Self-check | 2-3x quality improvement |
| 14 | ultrathink | Deep reasoning для сложных задач |
| 15 | Paste raw data | Точный root cause |
| 16 | @ file references | Пропуск поиска, экономия токенов |
| 17 | Vague prompts | Exploration незнакомого кода |
| 18 | 2 corrections → fresh | Escape from rabbit holes |
| 19 | Interview pattern | Complete spec через Q&A |
| 20 | Explore unfamiliar | Onboarding через open questions |

### Workflow (Practices 21-35)

| # | Практика | Impact |
|---|----------|--------|
| 21 | /clear between tasks | Предотвращает context degradation |
| 22 | Plan Mode | Предотвращает wrong-problem solving |
| 23 | Ctrl+G edit plans | Direct plan manipulation |
| 24 | /btw | Side questions без загрязнения контекста |
| 25 | Ctrl+S stash | Не потерять draft |
| 26 | Ctrl+B background | Параллельная работа |
| 27 | /loop | Автоматический мониторинг |
| 28 | --worktree | Isolated parallel branches |
| 29 | /branch | Try альтернативный подход |
| 30 | Write + review | Two-Claude quality assurance |
| 31 | Naming + colors | Session identification |
| 32 | Guide compaction | Контролируемая компрессия |
| 33 | Subagents | Clean main context |
| 34 | Custom subagents | Recurring specialised tasks |
| 35 | Agent teams | Multi-session parallelism |

### Hooks (Practices 36-39)

| # | Практика | Impact |
|---|----------|--------|
| 36 | Auto-format | Consistent formatting |
| 37 | Block destructive | Prevent catastrophic commands |
| 38 | Preserve on compaction | Context survival |
| 39 | Sound notification | Awareness без monitoring |

### Safety (Practices 40-44)

| # | Практика | Impact |
|---|----------|--------|
| 40 | /sandbox | OS-level isolation |
| 41 | /permissions whitelist | Uninterrupted flow |
| 42 | Manual review auth/payments | Human judgement on critical paths |
| 43 | Conversational PR reviews | Deeper issue detection |
| 44 | Fan-out batch | Parallel file processing |

### Advanced (Practices 45-50)

| # | Практика | Impact |
|---|----------|--------|
| 45 | Voice dictation | Richer, faster prompts |
| 46 | Remote control | Mobile monitoring |
| 47 | Output style | Tailored responses |
| 48 | Status line | Real-time session awareness |
| 49 | Context management | Proactive control |
| 50 | Custom spinners | Developer experience joy |

---

## Рекомендации по внедрению

### Для начинающих (первая неделя)

1. Настройте aliases и LSP plugin (Practices 1-2)
2. Освойте `/clear` и базовые keyboard shortcuts (Practice 21)
3. Используйте `@` для указания файлов (Practice 16)
4. Установите `gh` CLI (Practice 3)

### Для промежуточного уровня (2-4 недели)

5. Создайте CLAUDE.md с litmus test подходом (Practices 5, 7)
6. Настройте hooks для formatting и destructive command blocking (Practices 36-37)
7. Начните использовать Plan Mode и subagents (Practices 22, 33)
8. Попробуйте voice input (Practice 45)

### Для продвинутых (1+ месяц)

9. Multi-Claude workflows с worktrees (Practices 28, 30)
10. Agent teams для параллельной работы (Practice 35)
11. Custom subagents и skills для recurring tasks (Practices 11, 34)
12. Compaction hooks и context preservation (Practices 32, 38)

---

## Резюме

Не нужны все 50 практик сразу. Выберите одну, которая решает самую раздражающую проблему из последней сессии, и попробуйте завтра. Одна практика, которая прижилась, стоит больше, чем пятьдесят в закладках.

**Три категории по приоритету:**

1. **Must-have** — Practices 2, 7, 10, 13, 21, 36, 42 (LSP plugin, CLAUDE.md litmus test, hooks vs CLAUDE.md, self-check, /clear, auto-format, manual review)
2. **High-value** — Practices 14, 15, 22, 28, 33, 37 (ultrathink, raw data, Plan Mode, worktrees, subagents, block destructive)
3. **Nice-to-have** — Practices 31, 45, 46, 50 (naming/colors, voice, remote, spinners)
