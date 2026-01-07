# OSS Recommendations for Studying Light

Goal: make the repository clear, trustworthy, and easy to adopt for new users and contributors.

## P01 - Add demo
- Add a demo data path or sample import file so users can see value in 5 minutes.

## P2 - Release and distribution
- Add a release workflow that tags versions and publishes GitHub Releases with notes from `CHANGELOG.md`.
- Publish a Docker image to GHCR and document `docker pull` usage in README.
- Add a compatibility section: supported Python, Node, and Docker versions.

## P2 - Discoverability and metadata
- Add badges for CI, license, version, and Docker image to README.
- Fill `pyproject.toml` metadata: license, authors, keywords, and project URLs.
- Add GitHub topics (reading, study, spaced-repetition, fastapi, react) to improve search visibility.

## P2 - Quality and maintenance
- Add tests that cover part creation, JSON import, review item generation, and `/today` (as required by AGENTS).
- Add a minimal coverage report (pytest-cov) and badge if useful for contributors.
- Consider a CI matrix for supported Python versions if you plan to support more than 3.12.

## P3 - Product polish and marketing
- Add a short demo video or GIF to show the core flow.
- Add a Roadmap or Milestones doc in `docs/` with 3-5 near-term goals.
- Add a FAQ and "Why this exists" section to connect with users.
