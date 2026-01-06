# Database storage and backups

## Persistence
- The SQLite file lives at `data/app.db` for local runs.
- Docker uses `/data/app.db` and `docker-compose.yml` bind-mounts `./data` to `/data`, so rebuilds and container removal keep the database as long as `./data` remains.

## Backups
- Run `make backup` or `uv run python -m studying_light.db.backup` to create a timestamped copy.
- Backups go to `data/backups/` (or `/data/backups` in Docker).
- Use `--output-dir` to override the backup directory.
- Only file-based SQLite URLs are supported.
