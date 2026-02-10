# Database (Postgres)

## Storage
- Docker uses PostgreSQL (`postgres:16-alpine`).
- Persistent data is stored in the named Docker volume `postgres_data`.
- Application container startup depends on a healthy Postgres container.

## Required configuration
- `DATABASE_URL` is required in Docker runtime.
- `docker-compose.yml` passes `IN_DOCKER=1`; if `DATABASE_URL` is missing, app startup fails with:
  - `{ "detail": "DATABASE_URL is required when running in Docker", "code": "DATABASE_URL_REQUIRED" }`

## Run and migrate
- Start stack: `cp .env.example .env && docker compose up --build`
- Run migrations in app container:
  - `docker compose run --rm --entrypoint uv -e DATABASE_URL=postgresql+psycopg://studying_light:studying_light@postgres:5432/studying_light app run alembic upgrade head`

## Migration smoke check (clean Postgres)
- Use `make postgres-alembic-smoke`.
- It validates:
  - clean DB `alembic upgrade head`
  - repeated `alembic upgrade head` (no-op)
  - `alembic downgrade -1` and back to `upgrade head`

## Admin/reset smoke check (Postgres)
- Use `make pg-smoke-admin`.
- It validates:
  - clean Postgres DB: `alembic upgrade head` and repeated no-op `upgrade head`
  - migration `0014_add_audit_log_and_admin_reset_fields` backfill path:
    - bootstrap DB to revision `0013`
    - insert legacy `password_reset_requests` row
    - upgrade to `head`
    - assert `requested_at` is backfilled from `created_at`
    - assert FK for `processed_by_admin_id` exists
  - admin/reset regression tests:
    - `tests/test_admin_api.py::test_admin_password_reset_flow_with_temp_password`
    - `tests/test_admin_api.py::test_admin_users_list_reports_online_after_heartbeat`
  - cleanup with `docker compose down -v`

## Backup and restore
- Backup:
  - `make pg-backup`
  - Output: `data/backups/studying_light.sql`
- Restore:
  - `make pg-restore BACKUP_FILE=data/backups/studying_light.sql`

## Manual pg_dump/pg_restore examples
- Dump:
  - `docker compose exec -T postgres pg_dump -U studying_light studying_light > data/backups/studying_light.sql`
- Restore:
  - `docker compose exec -T postgres psql -U studying_light -d studying_light < data/backups/studying_light.sql`
