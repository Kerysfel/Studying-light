.PHONY: run test lint format alembic docker-up backup

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
