# Database storage and backups

## Persistence
- If `DATABASE_URL` is set, the app uses that database (Postgres is supported).
- If `DATABASE_URL` is not set (or empty), the app falls back to SQLite via `DB_PATH`.
- The SQLite file lives at `data/app.db` for local runs.
- Docker uses `/data/app.db` and `docker-compose.yml` bind-mounts `./data` to `/data`, so rebuilds and container removal keep the database as long as `./data` remains.
- Docker Postgres stores data in the `postgres_data` volume.

## Postgres (Docker)
- Keep `DATABASE_URL` from `.env.example`, or set your own credentials.
- If you change credentials in `DATABASE_URL`, update the Postgres service values in `docker-compose.yml` to match.
- Start services: `docker compose --env-file .env up --build`.
- Migrations run on container start (`uv run alembic upgrade head`).
- To validate migrations on a clean database: `make postgres-migrations` (creates `studying_light_test`).

## Backups
SQLite:
- Run `make backup` or `uv run python -m studying_light.db.backup` to create a timestamped copy.
- Backups go to `data/backups/` (or `/data/backups` in Docker).
- Use `--output-dir` to override the backup directory.
- Only file-based SQLite URLs are supported.

Postgres (Docker):
- Example: `docker compose exec postgres pg_dump -U studying_light studying_light > data/backups/pg_dump.sql`
