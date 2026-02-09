# Studying Light

[![CI](https://github.com/Kerysfel/Studying-light/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Kerysfel/Studying-light/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Kerysfel/Studying-light/branch/main/graph/badge.svg)](https://codecov.io/gh/Kerysfel/Studying-light)
[![License](https://img.shields.io/github/license/Kerysfel/Studying-light)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Kerysfel/Studying-light)](https://github.com/Kerysfel/Studying-light/releases)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2FKerysfel%2Fstudying--light-2496ed?logo=docker)](https://github.com/Kerysfel/Studying-light/pkgs/container/studying-light)

Studying Light — легкий помощник для чтения и повторений. Отслеживайте книги,
делите их на части и планируйте повторения, чтобы лучше удерживать прочитанное.

![Dashboard](docs/screenshots/01-dashboard.png)

## Возможности

Есть сейчас:

- Книги и части с прогрессом.
- План повторений на сегодня.
- Сессия чтения: помодоро + цель по времени.
- Импорт JSON от GPT (сводка и вопросы).
- Повторения с сохранением GPT-оценки (JSON).
- Экспорт CSV/ZIP.
- Postgres + Alembic миграции.

В разработке:

- Импорт алгоритмов в БД через UI.
- Словарь алгоритмов (группы и карточки).
- Тренировки кода (typing / по памяти).

## Скриншоты

### План на сегодня

![Dashboard](docs/screenshots/01-dashboard.png)

### Сессия чтения (Pomodoro + заметки)

![Session](docs/screenshots/02-session.png)

### Генерация промптов (теория и алгоритмы)

![Prompts](docs/screenshots/03-prompts.png)

### Импорт JSON от GPT

![Import](docs/screenshots/04-import.png)

### Повторение

![Review](docs/screenshots/05-review.png)

## Документация

- Архитектура — как устроено: `docs/specs/architecture.md`
- Модель данных — таблицы/связи: `docs/specs/data-model.md`
- Правила повторений — интервалы и статусы: `docs/specs/review-scheduling.md`
- Границы API — что отдаёт фронту: `docs/specs/api-boundaries.md`
- Хранение и бэкапы — операционные инструкции: `docs/database.md`

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Данные Postgres сохраняются в volume `postgres_data`.

Откройте `http://localhost:8000` (фронт и API).

## Быстрый старт (локально)

```bash
uv sync --extra dev
DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light docker compose up -d postgres
DATABASE_URL=postgresql+psycopg://studying_light:studying_light@localhost:5432/studying_light uv run alembic upgrade head
uv run uvicorn studying_light.main:app --reload
```

Откройте `http://localhost:8000`.

Для локального запуска задайте `DATABASE_URL` на ваш Postgres.

Необязательный dev-сервер фронтенда:

```bash
cd frontend
npm install
npm run dev
```

Фронтенд будет доступен на `http://localhost:5173`.

## Как пользоваться

1) Создайте книгу (раздел “Книги”).
2) Start session → заметки → “Сгенерировать промпт”.
3) Вставьте промпт в ChatGPT, затем вставьте JSON в “Импорт JSON”.
4) Откройте “Повторения” → Start review → ответы → (опционально) GPT check.

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
| `APP_ENV`  | `docker`           | Метка окружения (`docker`/`local`). |
| `DATABASE_URL` | `postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light` | Основной URL базы данных. В Docker обязателен. |
| `TZ`       | `Europe/Amsterdam` | Часовой пояс контейнера.                                     |

## Статус проекта

Статус: beta (активная разработка). Интерфейсы могут меняться.

## Поддержка

- Issues: используйте GitHub Issues для багов и запросов функций.
- Discussions: используйте GitHub Discussions для вопросов.
- Security: используйте GitHub Security Advisories (private).

## Лицензия

MIT. См. `LICENSE`.
