# Studying Light

Сервис для сессий чтения, заметок и повторений с помощью интервальных вопросов.

![Главная страница](docs/image.png)

## Возможности

- Сессии чтения с заметками и таймерами.
- Импорт GPT JSON (summary + questions) и генерация повторений.
- Повторения по интервалам и дашборд на сегодня.
- Экспорт данных в CSV и ZIP.
- Шаблоны промптов на бэкенде.

## Стек

- Backend: FastAPI, SQLAlchemy, Alembic, SQLite.
- Frontend: Vite, React, Tailwind.
- API: `/api/v1`.

## Быстрый старт (Docker)

```bash
docker compose --env-file .env.example up --build
```

Откройте `http://localhost:8000`.

## Локальная разработка

Backend:

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn studying_light.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Экспорт

- `GET /api/v1/export.csv`
- `GET /api/v1/export.zip`

## License

MIT. См. `LICENSE`.

