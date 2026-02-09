# Архитектура

## Обзор
Studying Light состоит из SPA фронтенда и FastAPI бэкенда. Данные хранятся в
Postgres, миграции управляются Alembic.

## Компоненты
- Frontend: Vite + React (`frontend/`). В проде сборка кладется в `/app/static`
  и отдается бэкендом.
- Backend: FastAPI приложение (`src/studying_light`). Основной вход — `main.py`,
  API v1 подключен через `/api/v1`.
- Database: PostgreSQL через SQLAlchemy. В Docker используется сервис `postgres`.

## Поток данных
1. SPA обращается к JSON API `/api/v1`.
2. Бэкенд читает/пишет данные в Postgres и возвращает ответы.
3. Экспорт данных доступен через `/api/v1/export.csv` и `/api/v1/export.zip`.
