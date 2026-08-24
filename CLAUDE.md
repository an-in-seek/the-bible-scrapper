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
| `biblegateway.com` (`version=ASV`) | ASV (American Standard Version) | Implemented |
| `ebible.org` (`spaRV1909`) | RVR1909 (Reina Valera 1909, Spanish) | Implemented |
| `ebible.org` (`spablm`) | SBLM (Santa Biblia libre para el mundo, Spanish) | Implemented |
| `ebible.org` (`jpnm`) | JPNMEB (フリーダム・バイブル, Japanese) | Implemented |
| `jpn.bible` (`kougo`) | KOUGO (口語訳聖書 1954/1955, Japanese) | Implemented |

Design documents:

- [docs/nkrv-scraping-design.md](docs/nkrv-scraping-design.md) — NKRV
- [docs/world-english-bible-scraping-design.md](docs/world-english-bible-scraping-design.md) — WEB
- [docs/american-standard-version-scraping-design.md](docs/american-standard-version-scraping-design.md) — ASV
- [docs/reina-valera-1909-scraping-design.md](docs/reina-valera-1909-scraping-design.md) — RVR1909
- [docs/santa-biblia-libre-para-el-mundo-scraping-design.md](docs/santa-biblia-libre-para-el-mundo-scraping-design.md) — SBLM
- [docs/japanese-public-domain-scraping-design.md](docs/japanese-public-domain-scraping-design.md) — JPNMEB (Japanese)
- [docs/new-japanese-nt-scraping-design.md](docs/new-japanese-nt-scraping-design.md) — JPNLOC (Japanese NT, 설계만·미구현)
- [docs/japanese-colloquial-1955-scraping-design.md](docs/japanese-colloquial-1955-scraping-design.md) — KOUGO (口語訳 1954/1955)
- [docs/chinese-union-version-1919-scraping-design.md](docs/chinese-union-version-1919-scraping-design.md) — CUVT/CUVS (和合本 1919, 설계만·미구현)

## Common commands

```bash
pip install -r requirements.txt
pytest -q                                    # full test suite
pytest -q -k bskorea                         # single group
bash scripts/run_tests_wsl.sh                # WSL: create venv, install, run tests
python3 scripts/check_translation_drift.py --entry-url <URL> --head-only   # source Last-Modified
python3 scripts/check_translation_drift.py --translation-id <ID> --entry-url <URL>  # read-only diff
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

Data flow: read `bible_book` → build per-source chapter URLs → fetch HTML → parse verses → insert only missing chapters/verses → commit per chapter.

## Contracts that must hold

### Database

- **Never create `bible_book` rows.** The tool assumes all 66 books already exist for the target `translation_id` and only reads them. `bible_translation` is read-only as well.
- `bible_chapter` / `bible_verse` inserts are **missing-only**, so reruns are idempotent. Any change here needs an accompanying idempotency test.
- The flip side of missing-only: **a source that revises its text is never corrected by re-running.** Fine for fixed editions, not for drafts. Detect drift with `scripts/check_translation_drift.py` (read-only), then delete and re-load. `bible_chapter` and `bible_verse` carry **no foreign keys**, so deletion must go **verses first, then chapters** — dropping chapters first orphans the verses beyond the reach of any book-scoped query. Do not "fix" this by adding an overwrite mode; that changes the idempotency contract for every source.
- The transaction boundary is **per chapter**: a chapter row and its verses commit together. A failure mid-book keeps completed chapters and rolls back only the in-flight one; the retry re-processes the book and skips what already landed. Retries are still counted per book (`--book-retries`).
- `sync_identity_sequences()` runs at startup to align sequences with `MAX(id)`. Skipping it causes duplicate PK errors.

### Empty-data guards (intentional failures)

- A chapter that parses zero verses is skipped **before any write**, so no empty chapter row is ever committed. Same for a chapter whose first verse number is not `1`.
- If a whole book yields zero parsed verses, `process_book()` raises. Nothing was committed at that point, so the book is retried. Do not "fix" this by swallowing the exception.

### Parser fallback chain

`HolyBibleScraper._extract_verses()` is an ordered chain:

```
bskorea → biblegateway → ebible → jpnbible → bibletable → chapter-prefixed → ordered list → structured nodes → regex fallback
```

- **Source-specific parsers go first, generic inference parsers last.** If `_extract_verses_from_structured_nodes()` runs first, it misreads menus, footnotes, and dropdown text as verses.
- A source-specific parser must **return `[]`** when the page is not its source, so the chain can continue. It must not raise.
- `_extract_verses_from_bskorea_read_page()` calls `get_text("")` with no separator on purpose. Using `" "` splits Korean particles (e.g. `모세가` becomes `모세 가`).
- `h3` / `h4.psalm-title` removal is **not dead code**: ASV tags editorial headings and psalm superscriptions with the verse-1 class, so dropping the rule silently prepends them to verse 1. WEB pages contain no `h3` at all, which is why only the ASV tests cover it.
- `_extract_verses_from_biblegateway_passage()` reads verse numbers from the `span.text` **class token** (`Gen-2-1`), never from the rendered number: the first verse of a chapter displays the *chapter* number, so Genesis 2:1 would be stored as verse 2. It also merges same-numbered spans instead of deduplicating them (Psalms 23:4 arrives in four fragments) and drops `h4.psalm-title`, which carries the verse-1 class.
- `_extract_verses_from_ebible_page()` accumulates text **between** `span.verse` markers: on eBible the marker holds only the number and the body follows as sibling nodes. Verse numbers come from the `id` (`V12`), and chapter URLs pad the number per book — Psalms to three digits, everything else to two (`PSA23.htm` is a 404).
- `EBIBLE_REMOVABLE_SELECTOR` drops `div.d`, `div.qa`, `div.qd`, and `div.sp` because those headings sit **between** verse markers, so the accumulator folds them into the surrounding verse — measured on spablm as 21 leaked verses in Psalms 119 and 8 in Song of Songs 1. The contamination passes every automated check (verse count, contiguity, no empty verses), so only a targeted query or a human catches it. Never drop `div.q`/`div.q2`/`div.b` (they hold poetry text) or `span.wj` (words of Jesus).
- A `div.d` before the first verse marker is a **psalm superscription**, and it is deliberately not stored — matching KJV, NKRV, WEB, and ASV. RVR1909 is the lone exception only because that source inlines the superscription into verse 1 where the parser cannot separate it. Do not "fix" the difference by prepending it.
- Leaving eBible pages to the generic parsers is the worst case in this repo: the regex fallback returns a full, contiguous verse list with the number glued into verse 1, so verse-count and contiguity checks both pass.
- `_request_html()` re-decodes with `apparent_encoding` when `Content-Type` omits a charset. eBible declares UTF-8 only in a `<meta>` tag, and without this every Spanish accent is mojibake. Sources that send a charset are untouched — do not "simplify" this into an unconditional override.
- `_extract_verses_from_jpnbible_page()` receives a **chapter slice, not a page**: jpn.bible serves one page per book and has no per-chapter URL, so `_fetch_soup()` fetches the book once, splits it on `main.book > div[id]`, and hands over one `div`. Its guard is therefore `span.verse-content`, not `main.book`, and it also checks the chapter half of every verse `id`: handed a whole book page it would otherwise concatenate each chapter's verse 1 and return a plausible 67-verse list, so a slice spanning more than one chapter returns `[]` with a warning. Keying that split by `int` instead of the fragment string makes every lookup miss and every chapter come back empty.
- **`rt`/`rp` must be removed before the walk.** bs4 keeps furigana out of `get_text()`, but `RubyTextString`/`RubyParenthesisString` subclass `NavigableString`, so the descendants walk every accumulating parser here uses would fold `神（かみ）` into the verse. A `get_text()`-based test would pass while the DB fills with readings; measured at 2,197 of 2,205 sampled verses.
- On jpn.bible the verse `id` carries the whole range: `id="132:3 Ps.132.4 Ps.132.5"` means 3–5, and reading only the first extra token loses Psalms 132:5. `id="22:3!a"` is half of a split verse, and Exodus 22 prints `3!b` **before** `3!a`, so the halves join by suffix, not document order. A merged range is stored at every number it covers, which keeps verse numbering contiguous.
- jpn.bible leaves the opening bracket of a disputed passage at the end of the **previous** verse (19 verses, e.g. Matthew 17:20 ends with `〔`). The parser moves it to the head of the next verse; that is the only character-level edit made to this source, and it is what the second witness (`bible.religious-life.com`) does too.
- The four verses WEB leaves untranslated (Luke 17:36, Acts 8:37, 15:34, 24:7) are stored as `OMITTED_VERSE_TEXT` (`(omitted)`) rather than skipped, so contiguous verse numbering stays an invariant and any real gap reads as a scrape failure. The marker is written **only** when the span holds a `sup.footnote` and no body text — never for an arbitrarily empty span, or a DOM change would quietly fill the DB with placeholders instead of failing.
- `CJK_JOIN_PATTERN` strips the block-join space when **both** sides are CJK: Japanese and Chinese write no spaces between words, so the separator Spanish and English require corrupts them instead (measured on jpnm as 49% of sampled verses). Hangul is deliberately outside `CJK_RANGES` — Korean does space its words, and widening the range there repeats the bskorea particle bug in reverse. The test suite guards both directions.
- eBible's spablm omits **the same four verses** and needs the same treatment, which is why `EBIBLE_FOOTNOTE_SELECTOR` is separate from `EBIBLE_REMOVABLE_SELECTOR`: removal happens in two passes because stripping `a.notemark` first would destroy the only evidence that the empty verse was intentional. spaRV1909 carries all four as real text and must stay free of markers — check both translations after touching this.

### Adding a new source

In `scraper.py`:

1. `_is_<source>_source()`
2. `_build_<source>_url()`
3. `_discover_chapter_urls_for_<source>()` — reuse `KJV_CHAPTER_COUNTS` (shared across the 66-book canon)
4. `_extract_verses_from_<source>()` plus its slot in the `_extract_verses()` chain
5. branches in `get_source_name()`, `_build_chapter_url()`, `discover_chapter_urls_for_book()`

In `scrape_bible_to_db.py`:

6. `resolve_default_entry_url()` / `_is_nkrv_translation_hint()` — entry URL resolution
7. `TRANSLATION_SOURCE_REQUIREMENTS` — one row per translation, drives `validate_source_translation_compatibility()` in **both** directions (source must produce the translation, and the translation must come from that source). **Last line of defense against mis-loading**. The `version` token comes from `HolyBibleScraper.get_source_version()`, not from the URL query string: BibleGateway puts it in the query (`?version=ASV`) but eBible puts it in the path (`/spablm/`). When one source serves several translations, `_expected_translation_type()` returns the **first** matching row, so leaving `version` as `None` silently pins every translation of that source to whichever one is declared first.
8. `resolve_book_code_for_source()` — per-source book identifier

Skipping step 7 lets, for example, WEB text land under the KJV translation — expensive to undo.

### Environment variables

- `.env` is loaded with `os.environ.setdefault()`, so **shell environment variables win**.
- Translation resolution order: `BIBLE_TRANSLATION_ID` → lookup by (`BIBLE_TRANSLATION_TYPE`, `BIBLE_TRANSLATION_NAME`, `BIBLE_LANGUAGE_CODE`) → legacy default `translation_id=10`.
- That **legacy fallback of 10 is a trap**: with no variables set, data is silently written to translation 10.
- Entry URL comes from `KJV_ENTRY_URL` / `NKRV_ENTRY_URL` / `WEB_ENTRY_URL` / `ASV_ENTRY_URL` / `RVR1909_ENTRY_URL` / `SBLM_ENTRY_URL` / `JPNMEB_ENTRY_URL` / `KOUGO_ENTRY_URL`. A language code no longer identifies a source on its own: `en` covers KJV/WEB/ASV, `es` covers RVR1909/SBLM and `ja` covers JPNMEB/KOUGO, so with more than one URL of that language set, resolution raises rather than guessing. `BIBLE_TRANSLATION_ID` does **not** steer entry-URL selection, so an ID-only run can silently pick the wrong source; pass `BIBLE_TRANSLATION_TYPE` or `--entry-url`.
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
