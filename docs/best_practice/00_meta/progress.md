# Progress Log

## 2026-02-19
- Создан каркас учебника (`llm-handbook/*`).
- Импортирован исходный дайджест в `00_meta/source_digest.md`.
- Сформирован инвентарь URL: `00_meta/url_inventory.md`.
- Выделены нерепозиторные источники: `00_meta/url_non_repo.txt` (43 шт).
- Начат разбор ключевых источников по агентной разработке и MCP.

### Уже разобранные источники (v1 notes)
1. Anthropic Academy / Build with Claude (hub)
2. Claude Agent Skills overview
3. Claude Context Editing
4. Claude Code Hooks
5. Claude Code Sub-agents
6. Chrome DevTools MCP blog
7. Anthropic: Building agents with Claude Agent SDK
8. OpenAI: Introducing AgentKit

### Технические пометки
- Часть источников может редиректить/резаться по `web_fetch`.
- Для сложных страниц иногда нужен повторный fetch или альтернативный URL.

## 2026-02-20
- Продолжено наполнение учебника по плану.
- Добавлена глава `02_context-engineering/01_context_editing_compaction.md`.
- Добавлена глава `03_agents-mcp/01_subagents_skills_mcp.md`.
- Добавлена глава `03_agents-mcp/02_agent_skills_design.md`.
- Добавлена глава `06_devops/01_ci_agents_github_actions.md`.
- Добавлена глава `08_playbooks/01_frontend_runtime_debug_loop.md`.
- Добавлен source note: `sources/anthropic_claude_code_github_actions.md`.
- Проверен `cursor.com/cli` (данных мало; требуется дополнительный источник по деталям CLI/tooling).
- Попытка взять Google Gemini File Search через `web_fetch` дала redirect-ошибку (оставлено в очереди на повторную проверку URL).
- Добавлен source note: `sources/anthropic_build_with_claude_hub.md`.
- Добавлен source note: `sources/learnmcp_cloudflare_workers_guide.md`.
- Добавлен source note: `sources/vscode_mcp_registry_snapshot.md`.
- Пройден блок источников по MCP-экосистеме (partial), зафиксированы пробелы для deep-tech раздела.
- Добавлен source note: `sources/crewai_docs_overview.md`.
- Добавлен source note: `sources/firecrawl_overview.md`.
- Добавлен source note: `sources/mem0_overview.md`.
- Расширен coverage по инструментальному стеку (frameworks + data ingestion + memory layer).

## 2026-02-21
- Возобновлён проход по очереди non-repo источников (утренний слот).
- Перепроверен `https://code.visualstudio.com/mcp`:
  - подтверждён redirect в GitHub MCP Registry,
  - зафиксирован snapshot: `All MCP servers: 81`.
- Добавлен note по проблемному endpoint Cursor docs: `sources/cursor_docs_tools_redirect.md`.
- Обновлён note `sources/vscode_mcp_registry_snapshot.md` (свежий snapshot + практический вывод).
- Повторная попытка fetch `Gemini File Search` всё ещё упирается в redirect-loop — оставлено в очереди для browser-based съёма.
- Добавлены новые source notes:
  - `sources/google_gemini_code_assist_write_code.md`
  - `sources/supabase_overview.md`
  - `sources/ollama_overview.md`
  - `sources/lmstudio_overview.md`
  - `sources/warp_overview.md`
  - `sources/cursor_cli_overview.md`
  - `sources/cursor_learn_redirect.md`
- Обновлён `sources/anthropic_claude_code_github_actions.md` (добавлен alias URL `docs.anthropic.com`).
- Добавлены source notes: `sources/pocketbase_overview.md`, `sources/qoder_overview.md`, `sources/rube_overview_partial.md`, `sources/codewiki_partial.md`, `sources/gitvizz_partial.md`.
- Добавлен большой пакет source notes по оставшимся ссылкам: `kiro_overview`, `aitmpl_overview`, `stanford_cme295_syllabus`, `database_build_partial`, `decode_overview`, `dlai_live_voice_agents_adk`, `dlai_claude_code_course`, `deepsite_partial_signin`, `elysia_partial`, `n8nworkflows_catalog`, `google_agents_intensive_partial`, `sambanova_ace_open_source`, `stitch_partial`, `anthropic_ai_espionage_report`, `arxiv_2510_04618_ace`, `gemini_file_search_partial_redirect`.
- Итого покрытие non-repo ссылок доведено до **43/43** (100%).
- Handbook переразложен в формат полноценного курса:
  - добавлена программа `00_meta/course_program.md`,
  - добавлены module maps для разделов `01..09`,
  - добавлен `09_appendix/01_glossary.md`,
  - добавлен `10_capstone.md`,
  - `00_meta/README.md` обновлён под курсовой формат.
- Начато углубление модулей без искусственного раздувания (source-grounded):
  - `01_foundations/02_agent_loop_core_deep_dive.md`
  - `02_context-engineering/02_context_engineering_deep_dive.md`
  - `03_agents-mcp/03_agents_mcp_deep_dive.md`
  - принцип: только практики и выводы, подтверждённые `sources/*`.
- Довыполнено углубление всех модулей курса:
  - `04_rag/01_rag_systems_deep_dive.md`
  - `05_security/01_security_risk_deep_dive.md`
  - `06_devops/02_devops_for_agents_deep_dive.md`
  - `07_models/01_models_runtime_deep_dive.md`
  - `08_playbooks/02_workflow_playbooks_deep_dive.md`
- Добавлены поддерживающие документы курса:
  - `09_appendix/02_source_quality_map.md`
  - `10_capstone_rubric.md`

## 2026-02-24
- Добавлен milestone-план для frontend delivery: `08_playbooks/03_frontend_milestone_plan.md`.
- Обновлён `08_playbooks/00_module_map.md` (в lessons добавлен milestone-документ).
- Проведена базовая проверка структуры и ссылок модуля (наличие файлов/разделов) — блокирующих проблем не обнаружено.
- Формат статусов синхронизирован с операционным шаблоном: сделано / в работе / блокеры.
- Получена и зафиксирована методичка в проекте: `method.md`.
- Создан методологический контур `docs/*`:
  - `docs/spec.md`
  - `docs/changelog.md`
  - `docs/issues.md`
  - `docs/antipatterns.md`
  - `docs/dna-map.md`
  - `docs/benchmark.md`
  - `docs/results/phase-1-result.md`
- Сформирован frontend documentation pack (контрактный формат):
  - `docs/frontend-api-canonical.md`
  - `tests/contracts/frontend-api.contract.md`
  - `tests/checklists/frontend-readiness.checklist.md`
  - `tests/e2e-frontend-cases.md`
  - `docs/frontend-state-maps.md`
  - `docs/traceability-frontend.md`
