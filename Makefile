.PHONY: run test lint format alembic docker-up backup postgres-migrations

run:
	uv run uvicorn studying_light.main:app --reload

test:
	uv run --extra dev pytest --cov=studying_light --cov-report=term-missing

lint:
	uv run --extra dev ruff check .

format:
	uv run --extra dev black .

alembic:
	uv run alembic upgrade head

docker-up:
	docker compose --env-file .env up --build

backup:
	uv run python -m studying_light.db.backup

postgres-migrations:
	docker compose --env-file .env up -d postgres
	docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "DROP DATABASE IF EXISTS studying_light_test; CREATE DATABASE studying_light_test;"
	docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light_test app run alembic upgrade head
