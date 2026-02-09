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
- Логин: `POST /api/v1/auth/login` → `access_token`.
- Все доменные маршруты (`/api/v1/books`, `/api/v1/parts`, `/api/v1/reviews`, `/api/v1/algorithm-*`, `/api/v1/today`, `/api/v1/stats`, `/api/v1/export*`, `/api/v1/settings`) требуют заголовок `Authorization: Bearer <access_token>`.

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
