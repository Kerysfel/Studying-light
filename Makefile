.PHONY: run test lint format alembic docker-up postgres-migrations postgres-alembic-smoke pg-smoke-admin pg-backup pg-restore docker-config-smoke

DOCKER_DATABASE_URL ?= postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light
SMOKE_ADMIN_DB_CLEAN ?= studying_light_smoke_admin_clean
SMOKE_ADMIN_DB_BACKFILL ?= studying_light_smoke_admin_backfill
SMOKE_ADMIN_DB_URL_CLEAN ?= postgresql+psycopg://studying_light:studying_light@postgres:5432/$(SMOKE_ADMIN_DB_CLEAN)
SMOKE_ADMIN_DB_URL_BACKFILL ?= postgresql+psycopg://studying_light:studying_light@postgres:5432/$(SMOKE_ADMIN_DB_BACKFILL)

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

pg-smoke-admin:
	@set -eu; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose up -d postgres; \
	trap 'DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose down -v' EXIT; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose build app; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "DROP DATABASE IF EXISTS $(SMOKE_ADMIN_DB_CLEAN);"; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "CREATE DATABASE $(SMOKE_ADMIN_DB_CLEAN);"; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=$(SMOKE_ADMIN_DB_URL_CLEAN) app run alembic upgrade head; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=$(SMOKE_ADMIN_DB_URL_CLEAN) app run alembic upgrade head; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "DROP DATABASE IF EXISTS $(SMOKE_ADMIN_DB_BACKFILL);"; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d postgres -c "CREATE DATABASE $(SMOKE_ADMIN_DB_BACKFILL);"; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=$(SMOKE_ADMIN_DB_URL_BACKFILL) app run alembic upgrade 0013; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d $(SMOKE_ADMIN_DB_BACKFILL) -c "WITH selected_user AS (SELECT id FROM users WHERE email = 'legacy@local' LIMIT 1), ensured_user AS (INSERT INTO users (id, email, password_hash, is_active, is_admin) SELECT '00000000-0000-0000-0000-000000000001'::uuid, 'legacy@local', 'legacy-hash', true, false WHERE NOT EXISTS (SELECT 1 FROM selected_user) RETURNING id), target_user AS (SELECT id FROM ensured_user UNION ALL SELECT id FROM selected_user LIMIT 1) INSERT INTO password_reset_requests (user_id, status, created_at) SELECT id, 'requested', CURRENT_TIMESTAMP - INTERVAL '2 hours' FROM target_user;"; \
	DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose run --rm --entrypoint uv -e DATABASE_URL=$(SMOKE_ADMIN_DB_URL_BACKFILL) app run alembic upgrade head; \
	backfill_count=$$(DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d $(SMOKE_ADMIN_DB_BACKFILL) -tAc "SELECT COUNT(*) FROM password_reset_requests WHERE requested_at = created_at AND requested_at IS NOT NULL;" | tr -d '[:space:]'); \
	test "$$backfill_count" -eq 1; \
	fk_count=$$(DATABASE_URL=$(DOCKER_DATABASE_URL) docker compose exec -T postgres env PGPASSWORD=studying_light psql -U studying_light -d $(SMOKE_ADMIN_DB_BACKFILL) -tAc "SELECT COUNT(*) FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema WHERE tc.table_name = 'password_reset_requests' AND tc.constraint_type = 'FOREIGN KEY' AND kcu.column_name = 'processed_by_admin_id';" | tr -d '[:space:]'); \
	test "$$fk_count" -ge 1; \
	uv run --extra dev pytest -q tests/test_admin_api.py::test_admin_password_reset_flow_with_temp_password tests/test_admin_api.py::test_admin_users_list_reports_online_after_heartbeat

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
