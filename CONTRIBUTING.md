# Вклад в проект

Спасибо за интерес к Studying Light. Мы используем стандартный OSS-процесс:
форк, ветка, изменения, тесты и Pull Request.

## Требования

- Python и `uv` для бэкенда.
- Node.js и npm для фронтенда.

## Локальная настройка (backend)

```bash
cp .env.example .env
```

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn studying_light.main:app --reload
```

Открыть `http://localhost:8000`.

## Локальная настройка (frontend)

```bash
cd frontend
npm install
npm run dev
```

## Тесты, линт, формат

```bash
uv run pytest
```

```bash
uv run ruff check .
```

```bash
uv run black .
```

## Миграции

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Pull Requests

- Держите изменения сфокусированными на одной задаче.
- Следуйте существующим стилям и соглашениям.
- Добавляйте или обновляйте тесты при изменении поведения.
- Обновляйте документацию при необходимости.
- Избегайте несвязанных рефакторингов в одном PR.
- Запускайте Python только через `uv run` из корня репозитория.

## Сообщения коммитов

- Пишите короткие и понятные сообщения.
- Предпочитайте небольшие, удобные для ревью коммиты.
- Ссылайтесь на задачи или issue при необходимости.

## Code Review

- Будьте уважительны и конструктивны.
- Давайте контекст и объясняйте решения.
- Закрывайте обсуждения перед мерджем.
