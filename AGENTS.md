# Repository Guidelines

## Project Structure & Module Organization
- Core code lives at repository root.
- `scrape_bible_to_db.py`: CLI entrypoint and orchestration (book loop, retries, commits/rollbacks).
- `scraper.py`: HTTP fetching, link discovery, chapter/verse parsing with regex fallback.
- `db.py`: PostgreSQL connection and repository queries/inserts.
- `models.py`: DTOs (`Book`, `ChapterPayload`, `Verse`).
- `tests/`: unit tests (`tests/test_scraper.py`).
- `requirements.txt`: Python dependencies.

## Build, Test, and Development Commands
- Create environment and install dependencies:
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Run scraper (all books):
  - `python3 scrape_bible_to_db.py`
- Run a range:
  - `python3 scrape_bible_to_db.py --start-book 1 --end-book 3`
- Resume from latest completed book:
  - `python3 scrape_bible_to_db.py --resume`
- Genesis 1 smoke test (no DB insert):
  - `python3 scrape_bible_to_db.py --test-genesis1`
- Run unit tests:
  - `pytest -q`

## Coding Style & Naming Conventions
- Target Python 3.11+; follow PEP 8 with 4-space indentation.
- Use `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_CASE` for constants.
- Keep modules single-responsibility (CLI vs DB vs parsing).
- Add short, purpose-driven comments only where logic is non-obvious.

## Testing Guidelines
- Framework: `pytest`.
- Test files: `tests/test_*.py`; test functions: `test_*`.
- Prefer deterministic parser/unit tests using inline HTML fixtures.
- For DB-sensitive changes, include at least one idempotency test case (skip existing chapter/verse).

## Commit & Pull Request Guidelines
- No Git history is available in this directory; use Conventional Commit style by default:
  - `feat: add chapter discovery fallback`
  - `fix: prevent duplicate verse inserts`
- PRs should include:
  - concise summary of behavior change,
  - reproduction and verification commands,
  - schema/index impact (if any),
  - sample logs for scraper flow or error handling.

## Security & Configuration Tips
- Never hardcode DB credentials; use `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- Respect polite scraping delays and retry/backoff settings.
- Ensure inserts remain idempotent to support safe reruns.
