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


ENTRY_URL_ENV_BY_TRANSLATION_TYPE = {
    "KJV": "KJV_ENTRY_URL",
    "NKRV": "NKRV_ENTRY_URL",
    "WEB": "WEB_ENTRY_URL",
    "ASV": "ASV_ENTRY_URL",
}
# A language code alone does not identify a source: 'en' covers KJV, WEB and ASV.
TRANSLATION_TYPES_BY_LANGUAGE_CODE = {
    "ko": ("NKRV",),
    "en": ("KJV", "WEB", "ASV"),
}
LEGACY_TRANSLATION_TYPE_BY_ID = {"2": "NKRV"}
# Tie-break when nothing else narrows it down; keeps the pre-WEB default.
ENTRY_URL_PREFERENCE_ORDER = ("NKRV", "KJV", "WEB", "ASV")
# Which source may legitimately produce each translation, and how to recognise the
# translation when bible_translation.translation_type is empty. Drives the
# source/translation check in both directions, so adding a translation is one row.
TRANSLATION_SOURCE_REQUIREMENTS = {
    "KJV": {
        "source": "thekingsbible",
        "version": None,
        "name": "King James Version",
        "language_code": "en",
    },
    "NKRV": {
        "source": "bskorea",
        "version": "GAE",
        "name": "개역개정",
        "language_code": "ko",
    },
    "WEB": {
        "source": "biblegateway",
        "version": "WEB",
        "name": "World English Bible",
        "language_code": "en",
    },
    "ASV": {
        "source": "biblegateway",
        "version": "ASV",
        "name": "American Standard Version",
        "language_code": "en",
    },
}


def _configured_entry_urls() -> dict[str, str]:
    configured: dict[str, str] = {}
    for translation_type, env_name in ENTRY_URL_ENV_BY_TRANSLATION_TYPE.items():
        value = os.getenv(env_name)
        if value:
            configured[translation_type] = value
    return configured


def _translation_type_hint() -> str | None:
    declared = (os.getenv("BIBLE_TRANSLATION_TYPE") or "").strip().upper()
    if declared in ENTRY_URL_ENV_BY_TRANSLATION_TYPE:
        return declared

    translation_id = (os.getenv("BIBLE_TRANSLATION_ID") or "").strip()
    if translation_id in LEGACY_TRANSLATION_TYPE_BY_ID:
        return LEGACY_TRANSLATION_TYPE_BY_ID[translation_id]

    if (os.getenv("BIBLE_TRANSLATION_NAME") or "").strip() == "개역개정":
        return "NKRV"

    return None


def resolve_default_entry_url() -> str:
    configured = _configured_entry_urls()
    if not configured:
        return DEFAULT_ENTRY_URL

    hint = _translation_type_hint()
    if hint is not None and hint in configured:
        return configured[hint]

    language_code = (os.getenv("BIBLE_LANGUAGE_CODE") or "").strip().lower()
    by_language = [
        translation_type
        for translation_type in TRANSLATION_TYPES_BY_LANGUAGE_CODE.get(language_code, ())
        if translation_type in configured
    ]
    if len(by_language) == 1:
        return configured[by_language[0]]
    if len(by_language) > 1:
        env_names = ", ".join(
            ENTRY_URL_ENV_BY_TRANSLATION_TYPE[translation_type] for translation_type in by_language
        )
        raise ValueError(
            f"Ambiguous entry URL: BIBLE_LANGUAGE_CODE={language_code!r} matches {env_names}. "
            "Set BIBLE_TRANSLATION_TYPE or pass --entry-url explicitly."
        )

    if len(configured) == 1:
        return next(iter(configured.values()))

    for translation_type in ENTRY_URL_PREFERENCE_ORDER:
        if translation_type in configured:
            return configured[translation_type]

    return DEFAULT_ENTRY_URL


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
        default=None,
        help=(
            "Source entry URL "
            "(default: env KJV_ENTRY_URL, NKRV_ENTRY_URL, WEB_ENTRY_URL, or built-in default)"
        ),
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


def _expected_translation_type(source_name: str, version: str | None) -> str | None:
    """Translation this source/version combination is expected to produce."""
    for translation_type, requirement in TRANSLATION_SOURCE_REQUIREMENTS.items():
        if requirement["source"] != source_name:
            continue
        required_version = requirement["version"]
        if required_version is None or required_version == version:
            return translation_type
    return None


def _translation_type_by_identity(name: str, language_code: str) -> str | None:
    """Recognise a translation from its name/language when translation_type is empty."""
    for translation_type, requirement in TRANSLATION_SOURCE_REQUIREMENTS.items():
        if requirement["name"] == name and requirement["language_code"] == language_code:
            return translation_type
    return None


def validate_source_translation_compatibility(
    repo: BibleRepository,
    conn,
    scraper: HolyBibleScraper,
) -> None:
    """
    Last line of defense against loading one translation's text under another's books.

    Checks both directions: the source must produce the resolved translation, and the
    resolved translation must come from that source.
    """
    metadata = repo.get_translation_metadata(conn)
    source_name = scraper.get_source_name()
    parsed_entry = urlparse(scraper.entry_url)
    query_params = dict(parse_qsl(parsed_entry.query, keep_blank_values=True))
    version = query_params.get("version")

    translation_type = str(metadata.get("translation_type") or "")
    translation_name = str(metadata.get("name") or "")
    language_code = str(metadata.get("language_code") or "")

    expected_type = _expected_translation_type(source_name, version)

    if expected_type is not None:
        if translation_type == expected_type:
            return

        requirement = TRANSLATION_SOURCE_REQUIREMENTS[expected_type]
        if translation_type:
            raise RuntimeError(
                f"Source/translation mismatch: {source_name} source"
                + (f" (version={version})" if version else "")
                + f" requires translation_type={expected_type!r}, "
                f"but resolved translation metadata={metadata}"
            )

        # translation_type is empty: fall back to name/language identity.
        if (
            translation_name == requirement["name"]
            and language_code == requirement["language_code"]
        ):
            logging.warning(
                "Translation metadata matched %s by name/language but translation_type was empty",
                expected_type,
            )
            return

        conflicting = _translation_type_by_identity(translation_name, language_code)
        if conflicting is not None:
            raise RuntimeError(
                f"Source/translation mismatch: {source_name} source requires "
                f"translation_type={expected_type!r}, but the metadata identifies "
                f"{conflicting!r}. Resolved translation metadata={metadata}"
            )

        logging.warning(
            "translation_type is empty and the metadata does not identify a known "
            "translation; source/translation compatibility could not be verified. "
            "Resolved translation metadata=%s",
            metadata,
        )
        return

    # The source has no expected translation (e.g. an unmapped biblegateway version).
    # Still refuse when the resolved translation belongs to a different source.
    requirement = TRANSLATION_SOURCE_REQUIREMENTS.get(translation_type)
    if requirement is None:
        return

    if requirement["source"] != source_name:
        raise RuntimeError(
            f"Source/translation mismatch: translation_type={translation_type!r} must be "
            f"loaded from {requirement['source']!r}, not {source_name!r}. "
            f"Resolved translation metadata={metadata}"
        )

    if requirement["version"] is not None and version is not None and requirement["version"] != version:
        raise RuntimeError(
            f"Source/translation mismatch: translation_type={translation_type!r} requires "
            f"version={requirement['version']!r}, but the entry URL uses version={version!r}. "
            f"Resolved translation metadata={metadata}"
        )


def resolve_book_code_for_source(scraper: HolyBibleScraper, book: Book) -> str | None:
    source_name = scraper.get_source_name()

    if source_name == "biblegateway":
        # BibleGateway expects a readable book name ("1 Samuel"), not a key like
        # "1SA", so the constant table wins over bible_book.book_key here.
        return scraper._get_biblegateway_book_name(book.book_order)

    if source_name != "bskorea":
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
    Process one book, committing after each chapter.

    A chapter row and its verses are written in the same transaction, so a failure
    mid-book leaves completed chapters durable and never leaves a chapter row
    without verses. Chapters that parse nothing are skipped before any write.

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

    inserted_chapters_total = 0
    inserted_verses_total = 0
    parsed_verses_total = 0

    for chapter_number in chapter_numbers:
        chapter_url = chapter_urls[chapter_number]
        logging.info(
            "[BOOK %02d][CH %03d] Fetching...",
            book.book_order,
            chapter_number,
        )

        # Fetch before touching the DB so a skipped chapter opens no transaction.
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

        chapter_id = chapter_map.get(chapter_number)
        if chapter_id is None:
            repo.insert_missing_chapters(conn, book.id, [chapter_number])
            chapter_map = repo.get_chapter_map(conn, book.id)
            chapter_id = chapter_map[chapter_number]
            inserted_chapters_total += 1

        existing_numbers = repo.get_existing_verse_numbers(conn, chapter_id)
        new_verses = [v for v in payload.verses if v.verse_number not in existing_numbers]
        inserted = repo.insert_missing_verses(conn, chapter_id, new_verses)

        conn.commit()  # chapter-level commit

        parsed_verses_total += len(payload.verses)
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
        inserted_chapters_total,
        inserted_verses_total,
    )

    if parsed_verses_total == 0:
        # Nothing was committed: every chapter was skipped before its write.
        raise RuntimeError(
            f"[BOOK {book.book_order}] Parsed 0 verses across all chapters; "
            "no chapter was committed."
        )

    return len(chapter_numbers), inserted_chapters_total, inserted_verses_total


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
        # Resolved after parsing so an explicit --entry-url skips resolution entirely.
        entry_url = args.entry_url or resolve_default_entry_url()
    except ValueError as exc:
        logging.error(str(exc))
        return 2

    scraper = HolyBibleScraper(entry_url=entry_url)

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
                    # process_book() already committed each chapter; this only
                    # closes the empty transaction left open by the last read.
                    conn.commit()
                    logging.info("[BOOK %02d] COMPLETED", book.book_order)
                    completed = True
                    break
                except Exception:
                    # Discards only the in-flight chapter; committed ones stay.
                    conn.rollback()
                    logging.exception(
                        "[BOOK %02d] attempt=%d/%d failed, rolled back in-flight chapter",
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
