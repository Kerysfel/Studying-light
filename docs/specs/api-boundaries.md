# Границы API

## Публичные HTTP интерфейсы
- `/`: SPA фронтенд (fallback для пользовательских маршрутов).
- `/assets`: статические файлы фронтенда.
- `/api/v1`: JSON API для книг, частей, повторений, дашборда, настроек, аутентификации и экспорта.
- `/prompts/{name}`: текстовые промпты (plain text).
- `/health`: простой health-check.
- `/docs` и `/openapi.json`: интерактивная документация и OpenAPI схема.

## Что считается API
- JSON ответы доступны только под `/api/v1`.
- `/prompts/{name}` возвращает plain text и не входит в JSON API.
- Остальные маршруты обслуживают SPA и статику.

## Аутентификация
- Регистрация: `POST /api/v1/auth/register`.
- Логин: `POST /api/v1/auth/login` → JWT `access_token`.
- Профиль: `GET /api/v1/auth/me` (требует Bearer токен).
- Heartbeat online: `POST /api/v1/me/heartbeat` (требует Bearer токен).
- Запрос сброса пароля: `POST /api/v1/auth/request-password-reset` (всегда возвращает `{status:"ok"}`).
- Смена пароля: `POST /api/v1/auth/change-password` (требует Bearer токен).
- Все маршруты `/api/v1/*`, кроме `/api/v1/health` и `/api/v1/auth/*`, требуют заголовок `Authorization: Bearer <access_token>`.
- Ошибки аутентификации:
  - Нет токена: `401` с `code: "AUTH_REQUIRED"`.
  - Невалидный токен: `401` с `code: "AUTH_INVALID"`.

## Profile Backup/Restore API
- `GET /api/v1/profile-export.zip`:
  - Требует Bearer токен.
  - Возвращает ZIP (`application/zip`) с переносимым профилем пользователя.
  - Архив содержит:
    - `manifest.json`
    - `data/books.json`
    - `data/reading_parts.json`
    - `data/review_schedule_items.json`
    - `data/review_attempts.json`
    - `data/algorithm_groups.json`
    - `data/algorithms.json`
    - `data/algorithm_code_snippets.json`
    - `data/algorithm_review_items.json`
    - `data/algorithm_review_attempts.json`
    - `data/algorithm_training_attempts.json`
    - `data/user_settings.json` (опционально)
  - Все JSON-файлы: массивы объектов.
  - `manifest.json` включает:
    - `format: "studying-light-profile"`
    - `format_version: 1`
    - `exported_at` (ISO8601)
    - `app_version`
    - `counts` (количество записей по сущностям)
    - `sha256` (контрольные суммы для `data/*.json`)
    - `intervals_days` (опционально, snapshot из `user_settings`)
- `POST /api/v1/profile-import?mode=merge|replace&confirm_replace=true|false`:
  - Требует Bearer токен.
  - `multipart/form-data`: `file=<zip>`.
  - `mode` по умолчанию `merge`.
  - `replace` требует явного `confirm_replace=true`.
  - Ответ:
    - `{ "status":"ok", "imported":{...}, "skipped":{...}, "warnings":[...] }`
  - Пример ответа:
    ```json
    {
      "status": "ok",
      "imported": {
        "books": 12,
        "reading_parts": 148,
        "review_schedule_items": 410,
        "review_attempts": 389,
        "algorithm_groups": 8,
        "algorithms": 57,
        "algorithm_code_snippets": 60,
        "algorithm_review_items": 210,
        "algorithm_review_attempts": 205,
        "algorithm_training_attempts": 73,
        "user_settings": 1
      },
      "skipped": {
        "user_settings": 0
      },
      "warnings": [
        "Found 14 imported books matching existing titles."
      ]
    }
    ```
  - Поведение:
    - `merge`: добавляет данные как новые записи; не переиспользует `id` из архива.
    - `replace`: удаляет доменные данные пользователя и импортирует архив заново.
    - `user_id` из архива игнорируется, всегда используется `current_user.id`.
  - Валидация импорта:
    - формат/версия манифеста;
    - обязательные файлы;
    - sha256 целостность;
    - минимальная schema-check в import models.
  - Лимиты и защита:
    - max archive size: 200MB;
    - max total extracted size: 400MB;
    - max files count: ограничено ожидаемой структурой архива;
    - запрет path traversal в ZIP entries (`..`, абсолютные пути);
    - ошибка лимитов: `PROFILE_IMPORT_TOO_LARGE`.

## Версионная совместимость profile-import
- `manifest.data_files` поддерживается как опциональное поле (если есть, используется для валидации состава архива).
- Для известных `data/*.json` допускается отсутствие файла, если:
  - `manifest.counts` для сущности равно `0`, или
  - ключ в `manifest.counts` отсутствует.
- Это позволяет импортировать архивы старых версий, где некоторые таблицы еще не экспортировались.

## Админ API
- Все `/api/v1/admin/*` требуют Bearer токен и `is_admin=true`.
- Для non-admin ответ: `403` с `code: "FORBIDDEN"`.
- Доступные endpoints:
  - `GET /api/v1/admin/users?query=&status=active|inactive`
  - `PATCH /api/v1/admin/users/{id}/activate`
  - `PATCH /api/v1/admin/users/{id}/deactivate`
  - `GET /api/v1/admin/password-resets?status=requested|processed`
  - `POST /api/v1/admin/password-resets/{request_id}/issue-temp-password`
- Поле `online` в списке пользователей вычисляется на лету:
  - `online=true`, если `now - last_seen_at < 10 минут`.

## Формат ошибок
API возвращает единый формат ошибок:

```json
{
  "detail": "Validation error",
  "code": "VALIDATION_ERROR",
  "errors": [
    {"loc": ["body", "field"], "msg": "Invalid value", "type": "value_error"}
  ]
}
```
