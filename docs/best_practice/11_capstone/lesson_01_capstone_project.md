---
module: "11_capstone"
lesson: 1
title: "Задание на capstone-проект"
type: "practice"
prerequisites: ["10_tooling"]
difficulty: "advanced"
tags: ["capstone", "project", "end-to-end"]
---

# Module 10 — Capstone (Итоговый проект)

## Цель
Собрать end-to-end AI-систему с полным циклом: спецификация, агентная реализация, проверка, безопасность и операционная готовность.

## Обязательные артефакты
1. Product spec (что делаем и зачем)
2. Architecture + context strategy
3. Tooling/MCP map
4. RAG или data layer (если релевантно)
5. Security checklist + threat model
6. CI workflow с quality gates
7. Demo + postmortem

## Критерии защиты
- Воспроизводимость: другой инженер может повторить результат.
- Наблюдаемость: понятно, где и почему система ошибается.
- Управляемость стоимости: есть лимиты и бюджетные правила.
- Безопасность: нет критичных дыр по secret/tool/data.

## Рекомендуемый формат
- README (high-level)
- `/docs` (детали)
- `/playbooks` (операционные сценарии)
- 5–10 минут видео-демо или screencast
