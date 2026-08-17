# CLAUDE.md

Guidance for working in this repository. See [README.md](README.md) for usage details and [AGENTS.md](AGENTS.md) for general contribution rules.

## Overview

CLI tool that scrapes Bible text from source sites and loads it into PostgreSQL (`bible_chapter`, `bible_verse`).

Supported sources:

| Source | Translation | Status |
| --- | --- | --- |
| `thekingsbible.com` | KJV | Implemented |
| `bskorea.or.kr` (`version=GAE`) | NKRV | Implemented |
| `biblegateway.com` (`version=WEB`) | WEB (World English Bible) | Implemented |

Design documents:

- [docs/nkrv-scraping-design.md](docs/nkrv-scraping-design.md) — NKRV
- [docs/world-english-bible-scraping-design.md](docs/world-english-bible-scraping-design.md) — WEB

## Common commands

```bash
pip install -r requirements.txt
pytest -q                                    # full test suite
pytest -q -k bskorea                         # single group
bash scripts/run_tests_wsl.sh                # WSL: create venv, install, run tests
python3 scrape_bible_to_db.py --test-genesis1              # parser-only check, no DB
python3 scrape_bible_to_db.py --test-book 3 --test-chapter 11
python3 scrape_bible_to_db.py --start-book 1 --end-book 3  # actual load
```

Use `python` on Windows and `python3` on WSL/Linux. Changes must work on both.

## Architecture

```
scrape_bible_to_db.py   CLI, book loop, retries, commit/rollback, source/translation validation
  └ scraper.py          HTTP, retry/throttle, per-source URL building, chapter/verse parsing
  └ db.py               psycopg2 connection, BibleRepository queries
  └ models.py           Book, ChapterPayload, Verse (DTOs)
scrape_kjv_to_db.py     Legacy wrapper; delegates to scrape_bible_to_db.run()
```

Data flow: read `bible_book` → build per-source chapter URLs → fetch HTML → parse verses → insert only missing chapters/verses → commit per book.

## Contracts that must hold

### Database

- **Never create `bible_book` rows.** The tool assumes all 66 books already exist for the target `translation_id` and only reads them. `bible_translation` is read-only as well.
- `bible_chapter` / `bible_verse` inserts are **missing-only**, so reruns are idempotent. Any change here needs an accompanying idempotency test.
- The transaction boundary is **per book**. A failure rolls back only that book and retries it; other books are unaffected.
- `sync_identity_sequences()` runs at startup to align sequences with `MAX(id)`. Skipping it causes duplicate PK errors.

### Empty-data guards (intentional failures)

- If a book yields zero parsed verses, `process_book()` raises and **blocks the commit**. This deliberately prevents storing an empty scrape result — do not "fix" it by swallowing the exception.
- If a chapter's first verse number is not `1`, that chapter is skipped.

### Parser fallback chain

`HolyBibleScraper._extract_verses()` is an ordered chain:

```
bskorea → biblegateway → bibletable → chapter-prefixed → ordered list → structured nodes → regex fallback
```

- **Source-specific parsers go first, generic inference parsers last.** If `_extract_verses_from_structured_nodes()` runs first, it misreads menus, footnotes, and dropdown text as verses.
- A source-specific parser must **return `[]`** when the page is not its source, so the chain can continue. It must not raise.
- `_extract_verses_from_bskorea_read_page()` calls `get_text("")` with no separator on purpose. Using `" "` splits Korean particles (e.g. `모세가` becomes `모세 가`).
- `_extract_verses_from_biblegateway_passage()` reads verse numbers from the `span.text` **class token** (`Gen-2-1`), never from the rendered number: the first verse of a chapter displays the *chapter* number, so Genesis 2:1 would be stored as verse 2. It also merges same-numbered spans instead of deduplicating them (Psalms 23:4 arrives in four fragments) and drops `h4.psalm-title`, which carries the verse-1 class.

### Adding a new source

In `scraper.py`:

1. `_is_<source>_source()`
2. `_build_<source>_url()`
3. `_discover_chapter_urls_for_<source>()` — reuse `KJV_CHAPTER_COUNTS` (shared across the 66-book canon)
4. `_extract_verses_from_<source>()` plus its slot in the `_extract_verses()` chain
5. branches in `get_source_name()`, `_build_chapter_url()`, `discover_chapter_urls_for_book()`

In `scrape_bible_to_db.py`:

6. `resolve_default_entry_url()` / `_is_nkrv_translation_hint()` — entry URL resolution
7. `validate_source_translation_compatibility()` — **last line of defense against mis-loading**
8. `resolve_book_code_for_source()` — per-source book identifier

Skipping step 7 lets, for example, WEB text land under the KJV translation — expensive to undo.

### Environment variables

- `.env` is loaded with `os.environ.setdefault()`, so **shell environment variables win**.
- Translation resolution order: `BIBLE_TRANSLATION_ID` → lookup by (`BIBLE_TRANSLATION_TYPE`, `BIBLE_TRANSLATION_NAME`, `BIBLE_LANGUAGE_CODE`) → legacy default `translation_id=10`.
- That **legacy fallback of 10 is a trap**: with no variables set, data is silently written to translation 10.
- Entry URL comes from `KJV_ENTRY_URL` / `NKRV_ENTRY_URL` / `WEB_ENTRY_URL`. `BIBLE_LANGUAGE_CODE=en` no longer identifies a source on its own — if both KJV and WEB URLs are set, resolution raises rather than guessing.
- Never hardcode DB credentials (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

### CLI argument constraints

- `--start-chapter` / `--end-chapter` are only valid without `--resume` and when `--start-book == --end-book`.
- `--resume` starts from the book after the **highest `book_order` that has at least one verse** — not after the last *complete* book. A partially loaded book is treated as done, so recover from failures by re-running an explicit book range instead.
- The `--test-*` smoke-test path **does not connect to the DB**. Preserve that property.

## Testing

- `pytest` with inline HTML fixtures. **Do not add tests that hit the network.**
- Parser changes need a fixture test for that source; DB changes need an idempotency test.
- `tests/conftest.py` puts the repo root on `sys.path`, so imports work from any working directory.

## Style

- Python 3.11+, PEP 8, 4-space indent. Use `from __future__ import annotations` with `X | None` syntax.
- `snake_case` / `PascalCase` / `UPPER_CASE`. Keep modules single-responsibility (CLI / parsing / DB).
- Comment only non-obvious logic, briefly.
- Follow the `[BOOK %02d][CH %03d]` log prefix convention.
- Commits use a Conventional Commit type with a Korean subject, e.g. `feat: WEB 소스 어댑터 추가`.

## Scraping etiquette

- Keep the polite per-request delay and the 5-second gap between books. Do not bypass the 429/5xx retry and throttle-multiplier logic.
- BibleGateway declares `Crawl-delay: 15`, enforced as a floor in `HolyBibleScraper.__init__` (`BIBLEGATEWAY_CRAWL_DELAY_SECONDS`). **Do not lower it** — a full 66-book load is meant to take ~5 hours.
- Check the target site's `robots.txt` and terms of use before adding a new source.
