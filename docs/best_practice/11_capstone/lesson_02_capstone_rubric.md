---
module: "11_capstone"
lesson: 2
title: "Рубрика оценки"
type: "reference"
prerequisites: ["11_capstone/lesson_01"]
difficulty: "advanced"
tags: ["rubric", "evaluation", "grading"]
---

# Capstone Rubric (100 points)

## 1. Spec quality (15)
- Чёткая цель, scope, constraints, done criteria.

## 2. Architecture & context strategy (15)
- Есть схема agent loop.
- Есть context/memory policy.

## 3. Tooling & orchestration (15)
- Обоснованный выбор tools/MCP.
- Явный orchestration flow.

## 4. Verification & testing (15)
- Автоматические проверки + ручные checkpoints.
- Evidence-driven результат.

## 5. Security & risk (15)
- Threat model.
- Guardrails + секреты + auditability.

## 6. DevOps & operability (10)
- CI/CD, лимиты, логи, rollback.

## 7. Cost/performance control (10)
- Бюджетные лимиты и измерения.

## 8. Documentation & reproducibility (5)
- Другой инженер может повторить.

## Passing threshold
- 70/100 и отсутствие критичных security провалов.
