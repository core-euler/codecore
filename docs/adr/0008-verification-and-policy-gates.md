# ADR 0008: Verification, Policy Gates, and Audit Trail

## Status
Accepted

## Date
2026-03-22

## Context

Без обязательной проверки агент остаётся генератором предположений. Без policy gates он становится опасным исполнителем. Для CodeCore, который претендует на серьёзную инженерную работу, эти два слоя должны быть встроены в runtime, а не висеть как опциональные советы.

## Decision

CodeCore запрещает считать задачу завершённой без evidence.

Обязательные классы verification:

- static verification;
- runtime verification;
- review layer;
- policy/security checks.

Policy engine принимает решения перед high-risk actions и может:

- allow;
- require approval;
- deny;
- downgrade route;
- request safer alternative.

Approval gates обязательны для:

- destructive file operations;
- production deploys;
- write в production DB;
- external side effects;
- large-blast-radius patches.

Каждый change flow должен быть аудируемым:

- кто инициировал задачу;
- какой pipeline выбран;
- какая модель предложила действие;
- какой tool применил его;
- какой diff внесён;
- какие проверки прошли или не прошли.

## Consequences

Плюсы:

- растёт доверие к системе;
- уменьшается число скрытых регрессий и опасных действий;
- можно строить review-ready reports и incident diagnosis;
- оператор получает прозрачность вместо слепой автоматики.

Минусы:

- сложнее UX и orchestration;
- некоторые задачи будут выполняться медленнее из-за проверок;
- нужна явная модель риска и интеграция с tool layer.

Принятый компромисс:

- безопасность и verification имеют приоритет над скоростью выполнения;
- быстрый unsafe path не считается допустимым основным режимом.
