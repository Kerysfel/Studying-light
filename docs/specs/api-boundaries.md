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
