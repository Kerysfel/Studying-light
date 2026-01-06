# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to
Semantic Versioning.

## [Unreleased]

## [0.2.0] - 2026-01-06

### Added

- Database backups command for SQLite.
- Book statistics for pages read and total reading time.
- Review list now shows upcoming scheduled items.
- Reading session now captures the last page and computes pages read.
- "Start session" button hides on the session page.
- Pomodoro timer shows work/rest, excludes rest from session time, and adapts cycles to the session target.

## [0.1.0] - 2026-01-01

### Added

- FastAPI backend with books, parts, reviews, dashboard, settings, and prompt endpoints.
- SQLite storage with Alembic migrations.
- CSV/ZIP export endpoints.
- Vite + React SPA with dashboard, reading session, import, and review flows.
- Docker/Compose setup with multi-stage frontend build.
- Backend review flow tests and Playwright smoke tests.
