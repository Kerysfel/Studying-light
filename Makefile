.PHONY: run test lint format alembic docker-up postgres-migrations postgres-alembic-smoke pg-backup pg-restore docker-config-smoke

DOCKER_DATABASE_URL ?= postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light

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
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose up --build

postgres-migrations:
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose up -d postgres
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose build app
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "DROP DATABASE IF EXISTS studying_light_test;"
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "CREATE DATABASE studying_light_test;"
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light_test app run alembic upgrade head

postgres-alembic-smoke:
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose up -d postgres
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose build app
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "DROP DATABASE IF EXISTS studying_light_smoke;"
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "CREATE DATABASE studying_light_smoke;"
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light_smoke app run alembic upgrade head
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light_smoke app run alembic upgrade head
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light_smoke app run alembic downgrade -1
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light_smoke app run alembic upgrade head

pg-backup:
	mkdir -p data/backups
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres pg_dump -U studying_light studying_light > data/backups/studying_light.sql

pg-restore:
	test -n "$(BACKUP_FILE)"
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres psql -U studying_light -d studying_light < $(BACKUP_FILE)

docker-config-smoke:
	@set +e; \
	output=$$(IN_DOCKER=1 APP_ENV=docker DATABASE_URL= uv run python -c "import studying_light.main" 2>&1); \
	status=$$?; \
	set -e; \
	if [ $$status -eq 0 ]; then \
		echo "Expected startup failure without DATABASE_URL in Docker mode"; \
		exit 1; \
	fi; \
	echo "$$output" | grep -q "DATABASE_URL_REQUIRED"; \
	echo "$$output" | grep -q "detail"; \
	echo "$$output"
