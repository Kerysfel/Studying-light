# Архитектура

## Обзор
Studying Light состоит из SPA фронтенда и FastAPI бэкенда. Данные хранятся в
SQLite, миграции управляются Alembic.

## Компоненты
- Frontend: Vite + React (`frontend/`). В проде сборка кладется в `/app/static`
  и отдается бэкендом.
- Backend: FastAPI приложение (`src/studying_light`). Основной вход — `main.py`,
  API v1 подключен через `/api/v1`.
- Database: SQLite через SQLAlchemy. По умолчанию `data/app.db`, в Docker — `/data/app.db`.

## Поток данных
1. SPA обращается к JSON API `/api/v1`.
2. Бэкенд читает/пишет данные в SQLite и возвращает ответы.
3. Экспорт данных доступен через `/api/v1/export.csv` и `/api/v1/export.zip`.
