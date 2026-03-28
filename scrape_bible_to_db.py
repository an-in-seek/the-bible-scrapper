from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from db import BibleRepository, get_db_connection
from models import Book
from scraper import DEFAULT_ENTRY_URL, HolyBibleScraper

BOOK_TRANSITION_DELAY_SECONDS = 5


def _is_nkrv_translation_hint() -> bool | None:
    translation_id = os.getenv("BIBLE_TRANSLATION_ID")
    translation_type = (os.getenv("BIBLE_TRANSLATION_TYPE") or "").strip().upper()
    translation_name = (os.getenv("BIBLE_TRANSLATION_NAME") or "").strip()
    language_code = (os.getenv("BIBLE_LANGUAGE_CODE") or "").strip().lower()

    if (
        translation_id == "2"
        or translation_type == "NKRV"
        or translation_name == "개역개정"
        or language_code == "ko"
    ):
        return True

    if (
        translation_type == "KJV"
        or language_code == "en"
    ):
        return False

    return None


def resolve_default_entry_url() -> str:
    kjv_entry_url = os.getenv("KJV_ENTRY_URL")
    nkrv_entry_url = os.getenv("NKRV_ENTRY_URL")

    if kjv_entry_url and nkrv_entry_url:
        nkrv_hint = _is_nkrv_translation_hint()
        if nkrv_hint is True:
            return nkrv_entry_url
        if nkrv_hint is False:
            return kjv_entry_url
        return nkrv_entry_url

    return kjv_entry_url or nkrv_entry_url or DEFAULT_ENTRY_URL


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_dotenv_file(env_path: str = ".env") -> None:
    """
    Lightweight .env loader (no external dependency).
    Existing environment variables are not overwritten.
    """
    path = Path(env_path)
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Bible text and insert into PostgreSQL")
    parser.add_argument("--start-book", type=int, default=1, help="Start book_order (1~66)")
    parser.add_argument("--end-book", type=int, default=66, help="End book_order (1~66)")
    parser.add_argument("--start-chapter", type=int, help="Start chapter number within a single selected book")
    parser.add_argument("--end-chapter", type=int, help="End chapter number within a single selected book")
    parser.add_argument("--test-book", type=int, help="Smoke-test target book_order (requires --test-chapter)")
    parser.add_argument("--test-chapter", type=int, help="Smoke-test target chapter number (requires --test-book)")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the next book of the latest completed book in DB",
    )
    parser.add_argument(
        "--entry-url",
        default=resolve_default_entry_url(),
        help="Source entry URL (default: env KJV_ENTRY_URL, NKRV_ENTRY_URL, or built-in default)",
    )
    parser.add_argument(
        "--book-retries",
        type=int,
        default=3,
        help="Retry count per book on failure",
    )
    parser.add_argument(
        "--test-genesis1",
        action="store_true",
        help="Run only Genesis chapter 1 parse test (no DB insert)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs")
    return parser.parse_args()


def validate_book_range(start_book: int, end_book: int) -> None:
    if start_book < 1 or end_book > 66 or start_book > end_book:
        raise ValueError("Invalid book range. Expected: 1 <= start-book <= end-book <= 66")


def validate_chapter_range(start_chapter: int | None, end_chapter: int | None) -> None:
    if start_chapter is None and end_chapter is None:
        return

    resolved_start = start_chapter or 1
    resolved_end = end_chapter or resolved_start
    if resolved_start < 1 or resolved_end < 1 or resolved_start > resolved_end:
        raise ValueError(
            "Invalid chapter range. Expected: 1 <= start-chapter <= end-chapter"
        )


def validate_chapter_selection_args(
    start_book: int,
    end_book: int,
    resume: bool,
    start_chapter: int | None,
    end_chapter: int | None,
) -> None:
    if start_chapter is None and end_chapter is None:
        return
    if resume:
        raise ValueError(
            "--start-chapter/--end-chapter cannot be used with --resume"
        )
    if start_book != end_book:
        raise ValueError(
            "--start-chapter/--end-chapter can only be used when exactly one book is selected"
        )


def validate_test_target_args(test_book: int | None, test_chapter: int | None) -> None:
    if test_book is None and test_chapter is None:
        return
    if test_book is None or test_chapter is None:
        raise ValueError("--test-book and --test-chapter must be provided together")
    if not (1 <= test_book <= 66) or test_chapter < 1:
        raise ValueError("Invalid smoke test target. Expected: 1 <= test-book <= 66 and test-chapter >= 1")


def run_chapter_smoke_test(
    scraper: HolyBibleScraper,
    book_order: int,
    chapter_number: int,
) -> None:
    """Simple runtime smoke test for one chapter."""
    logging.info("[TEST] Fetching book=%d chapter=%d...", book_order, chapter_number)
    payload = scraper.fetch_chapter_payload(book_order=book_order, chapter_number=chapter_number)

    if not payload.verses:
        raise RuntimeError(
            f"[TEST] Smoke test parse failed: no verses detected for book={book_order} chapter={chapter_number}"
        )

    logging.info("[TEST] book=%d chapter=%d parsed verses=%d", book_order, chapter_number, len(payload.verses))
    sample = payload.verses[0]
    logging.info("[TEST] Verse sample: %d %s", sample.verse_number, sample.text[:120])


def resolve_books(
    repo: BibleRepository,
    conn,
    start_book: int,
    end_book: int,
    resume: bool,
) -> list[Book]:
    resolved_start = start_book
    if resume:
        latest = repo.get_last_completed_book_order(conn)
        if latest is not None:
            resolved_start = max(start_book, latest + 1)
            logging.info("Resume enabled: latest completed=%s, next start=%s", latest, resolved_start)

    return repo.fetch_books(conn, resolved_start, end_book)


def validate_source_translation_compatibility(
    repo: BibleRepository,
    conn,
    scraper: HolyBibleScraper,
) -> None:
    metadata = repo.get_translation_metadata(conn)
    source_name = scraper.get_source_name()
    parsed_entry = urlparse(scraper.entry_url)
    query_params = dict(parse_qsl(parsed_entry.query, keep_blank_values=True))

    translation_type = str(metadata.get("translation_type") or "")
    translation_name = str(metadata.get("name") or "")
    language_code = str(metadata.get("language_code") or "")

    if source_name == "bskorea" and query_params.get("version") == "GAE":
        if translation_type == "NKRV":
            return
        if translation_name == "개역개정" and language_code == "ko":
            logging.warning(
                "Translation metadata matched NKRV by name/language but translation_type was %r",
                translation_type,
            )
            return
        raise RuntimeError(
            "Source/translation mismatch: bskorea GAE source requires "
            "translation_type='NKRV' (preferred), or at minimum name='개역개정' and "
            "language_code='ko'. "
            f"Resolved translation metadata={metadata}"
        )

    if source_name == "thekingsbible":
        if translation_type == "NKRV":
            raise RuntimeError(
                "Source/translation mismatch: thekingsbible source cannot be used with "
                "translation_type='NKRV'. "
                f"Resolved translation metadata={metadata}"
            )
        if translation_type == "" and translation_name == "개역개정" and language_code == "ko":
            raise RuntimeError(
                "Source/translation mismatch: thekingsbible source cannot be used with "
                "개역개정/ko translation metadata when translation_type is missing. "
                f"Resolved translation metadata={metadata}"
            )


def resolve_book_code_for_source(scraper: HolyBibleScraper, book: Book) -> str | None:
    if scraper.get_source_name() != "bskorea":
        return None

    candidate = (book.book_key or "").strip().lower()
    canonical = scraper._get_bskorea_book_code(book.book_order)
    if candidate:
        if canonical and candidate != canonical:
            logging.warning(
                "[BOOK %02d] book_key '%s' differs from canonical bskorea code '%s'; using book_key",
                book.book_order,
                candidate,
                canonical,
            )
        return candidate

    return canonical


def process_book(
    repo: BibleRepository,
    conn,
    scraper: HolyBibleScraper,
    book: Book,
    start_chapter: int | None = None,
    end_chapter: int | None = None,
) -> tuple[int, int, int]:
    """
    Process one book in current transaction.
    Returns: (chapter_count, inserted_chapter_count, inserted_verse_count)
    """
    logging.info("[BOOK %02d] Start: %s", book.book_order, book.name)
    book_code = resolve_book_code_for_source(scraper, book)

    chapter_urls = scraper.discover_chapter_urls_for_book(
        book.book_order,
        book_code=book_code,
    )
    if not chapter_urls:
        raise RuntimeError(f"[BOOK {book.book_order}] No chapter links discovered")

    if start_chapter is not None or end_chapter is not None:
        resolved_start = start_chapter or 1
        resolved_end = end_chapter or resolved_start
        chapter_urls = {
            chapter_number: chapter_url
            for chapter_number, chapter_url in chapter_urls.items()
            if resolved_start <= chapter_number <= resolved_end
        }
        if not chapter_urls:
            raise RuntimeError(
                f"[BOOK {book.book_order}] No chapter links found in requested range "
                f"{resolved_start}..{resolved_end}"
            )

    chapter_map = repo.get_chapter_map(conn, book.id)
    chapter_numbers = sorted(chapter_urls.keys())
    missing_chapters = [c for c in chapter_numbers if c not in chapter_map]
    inserted_chapters = repo.insert_missing_chapters(conn, book.id, missing_chapters)

    if missing_chapters:
        chapter_map = repo.get_chapter_map(conn, book.id)

    inserted_verses_total = 0
    parsed_verses_total = 0

    for chapter_number in chapter_numbers:
        chapter_id = chapter_map.get(chapter_number)
        if chapter_id is None:
            # Defensive fallback if map is stale.
            repo.insert_missing_chapters(conn, book.id, [chapter_number])
            chapter_map = repo.get_chapter_map(conn, book.id)
            chapter_id = chapter_map[chapter_number]

        chapter_url = chapter_urls[chapter_number]
        logging.info(
            "[BOOK %02d][CH %03d] Fetching...",
            book.book_order,
            chapter_number,
        )

        payload = scraper.fetch_chapter_payload(
            book.book_order,
            chapter_number,
            chapter_url,
            book_code=book_code,
        )
        if not payload.verses:
            logging.warning(
                "[BOOK %02d][CH %03d] No verses parsed (url=%s)",
                book.book_order,
                chapter_number,
                chapter_url,
            )
            continue
        if payload.verses[0].verse_number != 1:
            logging.warning(
                "[BOOK %02d][CH %03d] Suspicious verse start=%d; skip insert (url=%s)",
                book.book_order,
                chapter_number,
                payload.verses[0].verse_number,
                chapter_url,
            )
            continue

        parsed_verses_total += len(payload.verses)
        existing_numbers = repo.get_existing_verse_numbers(conn, chapter_id)
        new_verses = [v for v in payload.verses if v.verse_number not in existing_numbers]
        inserted = repo.insert_missing_verses(conn, chapter_id, new_verses)
        inserted_verses_total += inserted

        logging.info(
            "[BOOK %02d][CH %03d] verses parsed=%d, inserted=%d, skipped=%d",
            book.book_order,
            chapter_number,
            len(payload.verses),
            inserted,
            len(payload.verses) - inserted,
        )

    logging.info(
        "[BOOK %02d] Done. chapters=%d, inserted_chapters=%d, inserted_verses=%d",
        book.book_order,
        len(chapter_numbers),
        inserted_chapters,
        inserted_verses_total,
    )

    if parsed_verses_total == 0:
        raise RuntimeError(
            f"[BOOK {book.book_order}] Parsed 0 verses across all chapters; "
            "aborting commit to avoid storing empty scrape result."
        )

    return len(chapter_numbers), inserted_chapters, inserted_verses_total


def run() -> int:
    # Load .env first so argparse defaults and DB connection can use it.
    load_dotenv_file(".env")
    args = parse_args()
    configure_logging(args.verbose)

    try:
        validate_book_range(args.start_book, args.end_book)
        validate_chapter_range(args.start_chapter, args.end_chapter)
        validate_chapter_selection_args(
            start_book=args.start_book,
            end_book=args.end_book,
            resume=args.resume,
            start_chapter=args.start_chapter,
            end_chapter=args.end_chapter,
        )
        validate_test_target_args(args.test_book, args.test_chapter)
    except ValueError as exc:
        logging.error(str(exc))
        return 2

    scraper = HolyBibleScraper(entry_url=args.entry_url)

    # Smoke test path should not require DB connection.
    if args.test_genesis1 or args.test_book is not None:
        try:
            if args.test_book is not None and args.test_chapter is not None:
                run_chapter_smoke_test(
                    scraper=scraper,
                    book_order=args.test_book,
                    chapter_number=args.test_chapter,
                )
            else:
                run_chapter_smoke_test(scraper=scraper, book_order=1, chapter_number=1)
            return 0
        except Exception:
            logging.exception("[TEST] Smoke test failed")
            return 1
        finally:
            try:
                scraper.close()
            except Exception:
                pass

    repo = BibleRepository()
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        repo.sync_identity_sequences(conn)
        conn.commit()
        logging.info("DB identity sequences synced (bible_chapter, bible_verse)")
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)

        books = resolve_books(
            repo=repo,
            conn=conn,
            start_book=args.start_book,
            end_book=args.end_book,
            resume=args.resume,
        )

        if not books:
            logging.info("No target books found. Nothing to do.")
            return 0

        for book_index, book in enumerate(books):
            completed = False
            for attempt in range(1, args.book_retries + 1):
                try:
                    process_book(
                        repo=repo,
                        conn=conn,
                        scraper=scraper,
                        book=book,
                        start_chapter=args.start_chapter,
                        end_chapter=args.end_chapter,
                    )
                    conn.commit()  # book-level commit
                    logging.info("[BOOK %02d] COMMIT success", book.book_order)
                    completed = True
                    break
                except Exception:
                    conn.rollback()  # book-level rollback
                    logging.exception(
                        "[BOOK %02d] attempt=%d/%d failed, rolled back",
                        book.book_order,
                        attempt,
                        args.book_retries,
                    )
                    if attempt < args.book_retries:
                        time.sleep(min(2**attempt, 30))

            if not completed:
                logging.error("[BOOK %02d] permanently failed", book.book_order)
                return 1

            # Add a small cooldown between books to reduce source-site load.
            if book_index < len(books) - 1:
                logging.info(
                    "[BOOK %02d] Sleeping %ds before next book...",
                    book.book_order,
                    BOOK_TRANSITION_DELAY_SECONDS,
                )
                time.sleep(BOOK_TRANSITION_DELAY_SECONDS)

        logging.info("All requested books completed.")
        return 0

    except Exception:
        logging.exception("Fatal error")
        return 1
    finally:
        try:
            scraper.close()
        except Exception:
            pass
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(run())
