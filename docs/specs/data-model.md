# Модель данных

## Сущности

| Сущность | Назначение | Важные поля |
| --- | --- | --- |
| `Book` | Книга и ее статус. | `id`, `title`, `author`, `status`, `pages_total` |
| `ReadingPart` | Часть книги (сессия чтения). | `id`, `book_id`, `part_index`, `label`, `created_at`, `raw_notes`, `page_end`, `pages_read` |
| `ReviewScheduleItem` | Запланированное повторение. | `id`, `reading_part_id`, `interval_days`, `due_date`, `status`, `questions` |
| `ReviewAttempt` | Попытка прохождения повторения. | `id`, `review_item_id`, `answers`, `created_at`, `gpt_check_result` |
| `UserSettings` | Пользовательские настройки. | `id=1`, `timezone`, `pomodoro_*`, `daily_goal_*`, `intervals_days` |

## Связи

```
Book 1 ─── * ReadingPart 1 ─── * ReviewScheduleItem 1 ─── * ReviewAttempt
UserSettings (одна запись, id=1)
```
