"""CLI for backfilling user_activity_events from historical domain tables."""

from __future__ import annotations

import argparse
import logging

from studying_light.db.session import SessionLocal
from studying_light.services.backfill_user_activity_events import (
    backfill_user_activity_events,
    format_backfill_report,
)

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill user_activity_events from historical domain data."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and compute inserts without writing to the database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Commit interval for inserted rows (default: 200).",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    if args.batch_size <= 0:
        logger.error("Invalid --batch-size: must be positive")
        return 1

    session = SessionLocal()
    try:
        report = backfill_user_activity_events(
            session,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
        logger.info(format_backfill_report(report))
        if args.dry_run:
            logger.info("Dry-run mode: no data written.")
        return 0
    except Exception as exc:
        logger.error("Backfill failed: %s", exc)
        session.rollback()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
