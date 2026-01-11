"""SQLite backup utilities."""

import argparse
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine.url import make_url

from studying_light.db.session import build_database_url

logger = logging.getLogger(__name__)


def _sqlite_db_path(database_url: str) -> Path | None:
    """Return the SQLite database path from a SQLAlchemy URL."""
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return None
    if not url.database or url.database == ":memory:":
        return None
    return Path(url.database)


def backup_sqlite_db(output_dir: Path | None = None) -> Path:
    """Create a timestamped backup of the SQLite database."""
    database_url = build_database_url()
    db_path = _sqlite_db_path(database_url)
    if db_path is None:
        raise ValueError("Backups are supported only for file-based SQLite databases.")

    db_path = db_path.expanduser()
    if not db_path.is_absolute():
        db_path = db_path.resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    target_dir = output_dir or (db_path.parent / "backups")
    target_dir = target_dir.expanduser()
    if not target_dir.is_absolute():
        target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = target_dir / f"{db_path.stem}-{timestamp}{db_path.suffix}"

    with sqlite3.connect(db_path) as source, sqlite3.connect(backup_path) as dest:
        source.backup(dest)

    logger.info("Database backup created at %s", backup_path)
    return backup_path


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create a SQLite database backup.")
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory for backup files. Defaults to a 'backups' folder "
            "next to the DB."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Run the SQLite backup utility."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        backup_sqlite_db(output_dir=output_dir)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
