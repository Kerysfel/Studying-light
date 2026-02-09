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
- Запрос сброса пароля: `POST /api/v1/auth/request-password-reset` (всегда возвращает `{status:"ok"}`).
- Смена пароля: `POST /api/v1/auth/change-password` (требует Bearer токен).
- Все маршруты `/api/v1/*`, кроме `/api/v1/health` и `/api/v1/auth/*`, требуют заголовок `Authorization: Bearer <access_token>`.
- Ошибки аутентификации:
  - Нет токена: `401` с `code: "AUTH_REQUIRED"`.
  - Невалидный токен: `401` с `code: "AUTH_INVALID"`.

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
