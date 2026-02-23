# Модель данных

## Сущности

| Сущность | Назначение | Важные поля |
| --- | --- | --- |
| `Book` | Книга и ее статус. | `id`, `user_id`, `title`, `author`, `status`, `pages_total` |
| `ReadingPart` | Часть книги (сессия чтения). | `id`, `user_id`, `book_id`, `part_index`, `label`, `created_at`, `raw_notes`, `page_end`, `pages_read` |
| `ReviewScheduleItem` | Запланированное повторение. | `id`, `user_id`, `reading_part_id`, `interval_days`, `due_date`, `status`, `questions` |
| `ReviewAttempt` | Попытка прохождения повторения. | `id`, `user_id`, `review_item_id`, `answers`, `created_at`, `gpt_check_result`, `gpt_check_payload`, `gpt_rating_1_to_5`, `gpt_score_0_to_100`, `gpt_verdict` |
| `User` | Учетная запись пользователя. | `id`, `email`, `password_hash`, `is_active`, `is_admin`, `created_at`, `last_login_at`, `last_seen_at`, `must_change_password`, `temp_password_*` |
| `AlgorithmGroup` | Группа алгоритмов. | `id`, `user_id`, `title`, `title_norm`, `description`, `notes` |
| `Algorithm` | Алгоритм. | `id`, `user_id`, `group_id`, `source_part_id`, `title`, `summary`, `complexity` |
| `AlgorithmCodeSnippet` | Сниппет алгоритма. | `id`, `user_id`, `algorithm_id`, `code_kind`, `language`, `code_text` |
| `AlgorithmReviewItem` | Повторение алгоритма. | `id`, `user_id`, `algorithm_id`, `interval_days`, `due_date`, `status`, `questions` |
| `AlgorithmReviewAttempt` | Попытка повторения алгоритма. | `id`, `user_id`, `review_item_id`, `answers`, `rating_1_to_5`, `created_at` |
| `AlgorithmTrainingAttempt` | Тренировка алгоритма. | `id`, `user_id`, `algorithm_id`, `mode`, `code_text`, `rating_1_to_5`, `created_at` |
| `UserSettings` | Пользовательские настройки. | `user_id`, `timezone`, `pomodoro_*`, `daily_goal_*`, `intervals_days` |

## Связи

```
User 1 ─── * Book 1 ─── * ReadingPart 1 ─── * ReviewScheduleItem 1 ─── * ReviewAttempt
User 1 ─── * AlgorithmGroup 1 ─── * Algorithm 1 ─── * AlgorithmReviewItem 1 ─── * AlgorithmReviewAttempt
User 1 ─── * Algorithm 1 ─── * AlgorithmCodeSnippet
User 1 ─── * Algorithm 1 ─── * AlgorithmTrainingAttempt
User 1 ─── 1 UserSettings
```
