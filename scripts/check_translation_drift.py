#!/usr/bin/env python3
"""
Compare a loaded translation against its live source and report drifted verses.

Read-only: this script never writes to the database. It exists because
``bible_verse`` inserts are missing-only, so a source that revises its text
(eBible.org drafts do) will never be corrected by re-running the loader.
Use this to decide whether a re-load is warranted, then follow the procedure in
the source's design document.

    python3 scripts/check_translation_drift.py --translation-id 33 \
        --entry-url https://ebible.org/spaRV1909/GEN01.htm --start-book 1 --end-book 1

    # cheap first pass: just ask the server when the page was last regenerated
    python3 scripts/check_translation_drift.py --entry-url https://... --head-only

Each chapter's reads run in their own READ ONLY transaction that ends before the page
is fetched. A run takes hours on a crawl-delayed source, and the DB sits behind
Supabase's transaction-mode pooler: one transaction held for the whole run would pin a
backend and hold locks that block any ALTER TABLE until it finished.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import TextIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import BibleRepository, get_db_connection  # noqa: E402
from models import Book  # noqa: E402
from scrape_bible_to_db import (  # noqa: E402
    configure_logging,
    load_dotenv_file,
    resolve_book_code_for_source,
)
from scraper import HolyBibleScraper  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-url", required=True, help="Source entry URL to compare against")
    parser.add_argument("--translation-id", type=int, help="Target translation_id (default: BIBLE_TRANSLATION_ID)")
    parser.add_argument("--start-book", type=int, default=1)
    parser.add_argument("--end-book", type=int, default=66)
    parser.add_argument(
        "--head-only",
        action="store_true",
        help="Only report the entry URL's Last-Modified header, then exit",
    )
    parser.add_argument(
        "--max-report",
        type=int,
        default=40,
        help="Stop printing individual differences after this many (default: 40)",
    )
    parser.add_argument(
        "--output",
        help="Append every difference to this file as JSON lines (not capped by --max-report)",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def report_last_modified(scraper: HolyBibleScraper, url: str) -> None:
    response = scraper.session.get(url, timeout=30)
    response.raise_for_status()
    logging.info("Last-Modified: %s", response.headers.get("Last-Modified") or "(선언 없음)")
    logging.info("Content-Length: %s", response.headers.get("Content-Length") or "(선언 없음)")


def compare_book(
    scraper: HolyBibleScraper,
    repo: BibleRepository,
    conn,
    book: Book,
    max_report: int,
    reported: int,
    output: TextIO | None = None,
) -> tuple[int, int, int]:
    """Return (compared, drifted, reported) for one book."""
    chapter_map = repo.get_chapter_map(conn, book.id)
    conn.rollback()
    if not chapter_map:
        logging.warning("[BOOK %02d] DB에 장이 없다. 건너뛴다", book.book_order)
        return 0, 0, reported

    book_code = resolve_book_code_for_source(scraper, book)
    chapter_urls = scraper.discover_chapter_urls_for_book(book.book_order, book_code=book_code)

    compared = drifted = 0
    for chapter_number in sorted(chapter_map):
        chapter_id = chapter_map[chapter_number]
        stored = repo.get_verse_texts(conn, chapter_id)
        # End the read before the page fetch, which sleeps for the crawl delay.
        conn.rollback()

        payload = scraper.fetch_chapter_payload(
            book.book_order,
            chapter_number,
            chapter_urls.get(chapter_number),
            book_code=book_code,
        )
        if not payload.verses:
            logging.warning("[BOOK %02d][CH %03d] 소스 파싱 0절. 건너뛴다", book.book_order, chapter_number)
            continue

        live = {verse.verse_number: verse.text for verse in payload.verses}
        for number in sorted(set(stored) | set(live)):
            compared += 1
            before, after = stored.get(number), live.get(number)
            if before == after:
                continue
            drifted += 1
            if output is not None:
                output.write(json.dumps(
                    {
                        "book": book.book_order,
                        "chapter": chapter_number,
                        "verse": number,
                        "db": before,
                        "source": after,
                    },
                    ensure_ascii=False,
                ) + "\n")
                output.flush()
            if reported >= max_report:
                continue
            reported += 1
            kind = "DB에만" if after is None else ("소스에만" if before is None else "본문 상이")
            logging.info(
                "[BOOK %02d][CH %03d] %d절 %s\n    DB  : %s\n    소스: %s",
                book.book_order, chapter_number, number, kind,
                (before or "")[:120], (after or "")[:120],
            )
    return compared, drifted, reported


def main() -> int:
    args = parse_args()
    load_dotenv_file(".env")
    configure_logging(args.verbose)

    scraper = HolyBibleScraper(entry_url=args.entry_url)

    if args.head_only:
        report_last_modified(scraper, args.entry_url)
        return 0

    translation_id = args.translation_id
    if translation_id is None:
        raw = (os.getenv("BIBLE_TRANSLATION_ID") or "").strip()
        if not raw.isdigit():
            logging.error("--translation-id 를 주거나 BIBLE_TRANSLATION_ID 를 설정해야 한다")
            return 2
        translation_id = int(raw)

    repo = BibleRepository(translation_id=translation_id)
    conn = get_db_connection()
    # Not autocommit: set_session(readonly=True, autocommit=True) sends a session-level
    # SET that outlives this script on a pooled backend (see CLAUDE.md). Without it,
    # psycopg2 opens each transaction READ ONLY and leaves the session default alone.
    conn.set_session(readonly=True)
    output = None
    try:
        if args.output:
            output = open(args.output, "a", encoding="utf-8")
        books = repo.fetch_books(conn, args.start_book, args.end_book)
        conn.rollback()
        if not books:
            logging.error("translation_id=%s 에 해당 범위의 책이 없다", translation_id)
            return 2

        report_last_modified(scraper, args.entry_url)
        total_compared = total_drifted = 0
        reported = 0
        for book in books:
            compared, drifted, reported = compare_book(
                scraper, repo, conn, book, args.max_report, reported, output
            )
            total_compared += compared
            total_drifted += drifted
            logging.info(
                "[BOOK %02d] %s 비교 %d절 / 차이 %d절",
                book.book_order, book.name, compared, drifted,
            )

        logging.info("=" * 60)
        logging.info("비교 %d절 / 차이 %d절", total_compared, total_drifted)
        if total_drifted > args.max_report:
            logging.info("(개별 출력은 %d건에서 잘렸다)", args.max_report)
        if total_drifted:
            logging.warning("소스가 변경됐다. 재적재 절차는 해당 소스의 설계 문서를 따른다")
        return 1 if total_drifted else 0
    finally:
        if output is not None:
            output.close()
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
