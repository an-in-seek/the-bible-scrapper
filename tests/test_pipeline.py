import os

from models import Book, ChapterPayload, Verse
from scrape_bible_to_db import (
    process_book,
    resolve_book_code_for_source,
    resolve_default_entry_url,
    validate_chapter_range,
    validate_chapter_selection_args,
    validate_test_target_args,
    validate_source_translation_compatibility,
)


class FakeRepo:
    def __init__(self) -> None:
        self.chapter_map = {1: 1001}
        self.inserted_chapters: list[int] = []
        self.inserted_verses: list[tuple[int, list[Verse]]] = []

    def get_translation_metadata(self, conn):
        return conn.translation_metadata

    def get_chapter_map(self, conn, book_id: int) -> dict[int, int]:
        return dict(self.chapter_map)

    def insert_missing_chapters(self, conn, book_id: int, chapter_numbers: list[int]) -> int:
        self.inserted_chapters.extend(chapter_numbers)
        for chapter_number in chapter_numbers:
            self.chapter_map[chapter_number] = 2000 + chapter_number
        return len(chapter_numbers)

    def get_existing_verse_numbers(self, conn, chapter_id: int) -> set[int]:
        return conn.existing_verse_numbers.get(chapter_id, set())

    def insert_missing_verses(self, conn, chapter_id: int, verses: list[Verse]) -> int:
        self.inserted_verses.append((chapter_id, verses))
        return len(verses)


class FakeConn:
    def __init__(self) -> None:
        self.translation_metadata = {
            "id": 2,
            "language_code": "ko",
            "name": "개역개정",
            "translation_type": "NKRV",
        }
        self.existing_verse_numbers = {
            1001: {1},
            2002: set(),
        }


class FakeScraper:
    def __init__(self, entry_url: str) -> None:
        self.entry_url = entry_url
        self.discover_calls: list[tuple[int, str | None]] = []
        self.fetch_calls: list[tuple[int, int, str | None, str | None]] = []

    def get_source_name(self) -> str:
        return "bskorea"

    def _get_bskorea_book_code(self, book_order: int) -> str | None:
        if book_order == 3:
            return "lev"
        return None

    def discover_chapter_urls_for_book(self, book_order: int, book_code: str | None = None) -> dict[int, str]:
        self.discover_calls.append((book_order, book_code))
        return {
            1: "https://example.com/lev/1",
            2: "https://example.com/lev/2",
        }

    def fetch_chapter_payload(
        self,
        book_order: int,
        chapter_number: int,
        chapter_url: str | None = None,
        book_code: str | None = None,
    ) -> ChapterPayload:
        self.fetch_calls.append((book_order, chapter_number, chapter_url, book_code))
        if chapter_number == 1:
            verses = [
                Verse(verse_number=1, text="기존 절"),
                Verse(verse_number=2, text="새 절"),
            ]
        else:
            verses = [
                Verse(verse_number=1, text="둘째 장 첫 절"),
            ]

        return ChapterPayload(
            book_order=book_order,
            chapter_number=chapter_number,
            source_url=chapter_url or "",
            verses=verses,
        )


def test_validate_source_translation_compatibility_for_bskorea_gae() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_allows_name_language_fallback() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = {
        "id": 2,
        "language_code": "ko",
        "name": "개역개정",
        "translation_type": "",
    }
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_rejects_mismatched_translation() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = {
        "id": 10,
        "language_code": "en",
        "name": "King James Version",
        "translation_type": "KJV",
    }
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_rejects_thekingsbible_with_nkrv() -> None:
    repo = FakeRepo()
    conn = FakeConn()

    class KingsBibleScraper(FakeScraper):
        def get_source_name(self) -> str:
            return "thekingsbible"

    scraper = KingsBibleScraper("https://thekingsbible.com/Bible/1/1")

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_resolve_default_entry_url_prefers_nkrv_when_translation_hint_is_nkrv() -> None:
    original = {
        "KJV_ENTRY_URL": os.getenv("KJV_ENTRY_URL"),
        "NKRV_ENTRY_URL": os.getenv("NKRV_ENTRY_URL"),
        "BIBLE_TRANSLATION_ID": os.getenv("BIBLE_TRANSLATION_ID"),
        "BIBLE_TRANSLATION_TYPE": os.getenv("BIBLE_TRANSLATION_TYPE"),
        "BIBLE_TRANSLATION_NAME": os.getenv("BIBLE_TRANSLATION_NAME"),
        "BIBLE_LANGUAGE_CODE": os.getenv("BIBLE_LANGUAGE_CODE"),
    }
    try:
        os.environ["KJV_ENTRY_URL"] = "https://thekingsbible.com/Bible/1/1"
        os.environ["NKRV_ENTRY_URL"] = (
            "https://www.bskorea.or.kr/bible/korbibReadpage.php"
            "?version=GAE&book=gen&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
        )
        os.environ["BIBLE_TRANSLATION_TYPE"] = "NKRV"
        os.environ["BIBLE_TRANSLATION_NAME"] = "개역개정"
        os.environ["BIBLE_LANGUAGE_CODE"] = "ko"

        assert resolve_default_entry_url() == os.environ["NKRV_ENTRY_URL"]
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_resolve_book_code_for_source_prefers_book_key_when_it_differs_from_canonical() -> None:
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=lev&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )
    book = Book(
        id=69,
        book_order=3,
        book_key="WRONG",
        abbreviation="레",
        name="레위기",
    )

    assert resolve_book_code_for_source(scraper, book) == "wrong"


def test_process_book_reuses_existing_and_inserts_missing_using_book_key() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=lev&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )
    book = Book(
        id=69,
        book_order=3,
        book_key="LEV",
        abbreviation="레",
        name="레위기",
    )

    chapter_count, inserted_chapters, inserted_verses = process_book(
        repo=repo,
        conn=conn,
        scraper=scraper,
        book=book,
    )

    assert chapter_count == 2
    assert inserted_chapters == 1
    assert inserted_verses == 2
    assert repo.inserted_chapters == [2]
    assert scraper.discover_calls == [(3, "lev")]
    assert scraper.fetch_calls == [
        (3, 1, "https://example.com/lev/1", "lev"),
        (3, 2, "https://example.com/lev/2", "lev"),
    ]
    assert repo.inserted_verses[0][0] == 1001
    assert [verse.verse_number for verse in repo.inserted_verses[0][1]] == [2]
    assert repo.inserted_verses[1][0] == 2002
    assert [verse.verse_number for verse in repo.inserted_verses[1][1]] == [1]


def test_process_book_prefers_book_key_when_it_differs_from_canonical() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=lev&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )
    book = Book(
        id=69,
        book_order=3,
        book_key="WRONG",
        abbreviation="레",
        name="레위기",
    )

    process_book(
        repo=repo,
        conn=conn,
        scraper=scraper,
        book=book,
    )

    assert scraper.discover_calls == [(3, "wrong")]
    assert scraper.fetch_calls[0][3] == "wrong"


def test_process_book_filters_requested_chapter_range() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=lev&chap=11&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )
    book = Book(
        id=69,
        book_order=3,
        book_key="LEV",
        abbreviation="레",
        name="레위기",
    )

    chapter_count, inserted_chapters, inserted_verses = process_book(
        repo=repo,
        conn=conn,
        scraper=scraper,
        book=book,
        start_chapter=2,
        end_chapter=2,
    )

    assert chapter_count == 1
    assert inserted_chapters == 1
    assert inserted_verses == 1
    assert repo.inserted_chapters == [2]
    assert scraper.fetch_calls == [
        (3, 2, "https://example.com/lev/2", "lev"),
    ]


def test_validate_chapter_range_rejects_invalid_range() -> None:
    try:
        validate_chapter_range(12, 11)
    except ValueError as exc:
        assert "Invalid chapter range" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_validate_chapter_selection_args_requires_exactly_one_explicit_book() -> None:
    try:
        validate_chapter_selection_args(
            start_book=3,
            end_book=4,
            resume=False,
            start_chapter=11,
            end_chapter=11,
        )
    except ValueError as exc:
        assert "exactly one book" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_validate_chapter_selection_args_rejects_resume() -> None:
    try:
        validate_chapter_selection_args(
            start_book=3,
            end_book=3,
            resume=True,
            start_chapter=11,
            end_chapter=11,
        )
    except ValueError as exc:
        assert "cannot be used with --resume" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_validate_test_target_args_requires_both_values() -> None:
    try:
        validate_test_target_args(test_book=3, test_chapter=None)
    except ValueError as exc:
        assert "--test-book and --test-chapter" in str(exc)
    else:
        raise AssertionError("expected ValueError")
