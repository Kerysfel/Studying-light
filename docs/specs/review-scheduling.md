# Правила планирования повторений

## Интервалы
- Интервалы берутся из `UserSettings.intervals_days`.
- Если в настройках пусто, используются дефолтные значения: `[1, 7, 16, 35, 90]`.

## Генерация расписания
Расписание формируется в `POST /api/v1/parts/{part_id}/import_gpt`.

Шаги:
1. Сохраняются `gpt_summary` и `gpt_questions_by_interval`.
2. Все существующие `ReviewScheduleItem` для части удаляются.
3. Для каждого интервала создается новый `ReviewScheduleItem`:
   - `due_date = part.created_at.date + interval_days`
   - `status = planned`
   - `questions` берутся из `gpt_questions_by_interval`
     (ключ может быть `int` или `str`).

## Поведение в API
- `GET /api/v1/today` возвращает только элементы с `due_date == today`.
- `GET /api/v1/reviews/today` возвращает элементы с `due_date >= today`.
- `PATCH /api/v1/reviews/{review_id}` переносит дату только для `status=planned`.
- `POST /api/v1/reviews/{review_id}/complete` помечает `status=done`
  и создает `ReviewAttempt` с ответами.
- `POST /api/v1/reviews/{review_id}/save_gpt_feedback` сохраняет
  `gpt_check_result` в последнюю попытку.
