# Studying Light

[![CI](https://github.com/Kerysfel/Studying-light/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Kerysfel/Studying-light/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Kerysfel/Studying-light/branch/main/graph/badge.svg)](https://codecov.io/gh/Kerysfel/Studying-light)
[![License](https://img.shields.io/github/license/Kerysfel/Studying-light)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Kerysfel/Studying-light)](https://github.com/Kerysfel/Studying-light/releases)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2FKerysfel%2Fstudying--light-2496ed?logo=docker)](https://github.com/Kerysfel/Studying-light/pkgs/container/studying-light)

Studying Light — легкий помощник для чтения и повторений. Отслеживайте книги,
делите их на части и планируйте повторения, чтобы лучше удерживать прочитанное.

![Screenshot](docs/image.png)

## Возможности

- Учет книг и частей с планированием повторений.
- Сеансы чтения со статистикой и таймером в стиле Pomodoro.
- Экспорт CSV/ZIP.
- Локальное хранение в SQLite с резервными копиями.
- Бэкенд на FastAPI и фронтенд на React.

## Документация

- Архитектура: `docs/specs/architecture.md`
- Модель данных: `docs/specs/data-model.md`
- Правила повторений: `docs/specs/review-scheduling.md`
- Границы API: `docs/specs/api-boundaries.md`
- Хранение и бэкапы: `docs/database.md`

## Быстрый старт (Docker)

```bash
cp .env.example .env
```

При необходимости отредактируйте `.env`, затем:

```bash
docker compose --env-file .env up --build
```

Откройте `http://localhost:8000`.

## Быстрый старт (локально)

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn studying_light.main:app --reload
```

Откройте `http://localhost:8000`.

Необязательный dev-сервер фронтенда:

```bash
cd frontend
npm install
npm run dev
```

## API (справка)

Интерактивная документация: `http://localhost:8000/docs`.

Базовый префикс: `/api/v1`.

Пример: создать книгу

```bash
curl -X POST http://localhost:8000/api/v1/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Deep Work","author":"Cal Newport","pages_total":304}'
```

Ответ:

```json
{
  "id": 1,
  "title": "Deep Work",
  "author": "Cal Newport",
  "status": "active",
  "pages_total": 304,
  "pages_read_total": 0,
  "parts_total": 0,
  "sessions_total": 0,
  "reading_seconds_total": 0
}
```

Пример: план на сегодня

```bash
curl http://localhost:8000/api/v1/today
```

Ответ:

```json
{
  "active_books": [
    {
      "id": 1,
      "title": "Deep Work",
      "author": "Cal Newport",
      "status": "active",
      "pages_total": 304,
      "pages_read_total": 0
    }
  ],
  "review_items": [
    {
      "id": 10,
      "reading_part_id": 5,
      "interval_days": 7,
      "due_date": "2026-01-08",
      "status": "planned",
      "book_id": 1,
      "book_title": "Deep Work",
      "part_index": 2,
      "label": "Chapter 2"
    }
  ],
  "review_progress": {
    "total": 12,
    "completed": 4
  }
}
```

## Конфигурация

Значения по умолчанию ниже взяты из `.env.example`.

| Переменная | По умолчанию       | Примечания                                                   |
| ---------- | ------------------ | ------------------------------------------------------------ |
| `APP_ENV`  | `local`            | Метка окружения.                                             |
| `DB_PATH`  | `/data/app.db`     | Значение для Docker. Если локально не задано, то `data/app.db`. |
| `TZ`       | `Europe/Amsterdam` | Часовой пояс контейнера.                                     |

Необязательно:

- `DATABASE_URL`: переопределяет `DB_PATH`, если задана.

## Статус проекта

Статус: beta (активная разработка). Интерфейсы могут меняться.

## Поддержка

- Issues: используйте GitHub Issues для багов и запросов функций.
- Discussions: используйте GitHub Discussions для вопросов.
- Security: пишите на `newerasowwor@gmail.com`.

## Лицензия

MIT. См. `LICENSE`.
