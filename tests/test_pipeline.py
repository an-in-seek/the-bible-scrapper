import os

from models import Book, ChapterPayload, Verse
from scraper import HolyBibleScraper
from scrape_bible_to_db import (
    ENTRY_URL_ENV_BY_TRANSLATION_TYPE,
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
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeScraper:
    # Borrow the real version-token logic rather than re-implementing it, so these fakes
    # cannot drift from production behaviour. They only need `entry_url`.
    get_source_version = HolyBibleScraper.get_source_version
    _is_ebible_source = HolyBibleScraper._is_ebible_source
    _get_ebible_translation_code = HolyBibleScraper._get_ebible_translation_code
    _is_jpnbible_source = HolyBibleScraper._is_jpnbible_source
    _get_jpnbible_translation_code = HolyBibleScraper._get_jpnbible_translation_code
    _is_wikisource_source = HolyBibleScraper._is_wikisource_source
    _get_wikisource_variant = HolyBibleScraper._get_wikisource_variant
    _is_studybible_source = HolyBibleScraper._is_studybible_source
    _get_studybible_version = HolyBibleScraper._get_studybible_version

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
    # One commit per processed chapter.
    assert conn.commits == 2


def test_process_book_commits_after_each_chapter() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    scraper = FakeScraper(
        "https://www.bskorea.or.kr/bible/korbibReadpage.php"
        "?version=GAE&book=lev&chap=1&sec=1&cVersion=&fontSize=15px&fontWeight=normal"
    )
    book = Book(id=69, book_order=3, book_key="LEV", abbreviation="레", name="레위기")

    commit_marks: list[int] = []
    original_commit = conn.commit

    def tracking_commit() -> None:
        commit_marks.append(len(repo.inserted_verses))
        original_commit()

    conn.commit = tracking_commit  # type: ignore[method-assign]

    process_book(repo=repo, conn=conn, scraper=scraper, book=book)

    # Each commit lands right after that chapter's verse insert, not batched at the end.
    assert commit_marks == [1, 2]
    assert conn.rollbacks == 0


def test_process_book_does_not_create_chapter_row_when_no_verses_parsed() -> None:
    repo = FakeRepo()
    conn = FakeConn()

    class EmptyScraper(FakeScraper):
        def discover_chapter_urls_for_book(self, book_order, book_code=None):
            return {2: "https://example.com/lev/2"}

        def fetch_chapter_payload(self, book_order, chapter_number, chapter_url=None, book_code=None):
            return ChapterPayload(
                book_order=book_order,
                chapter_number=chapter_number,
                source_url=chapter_url or "",
                verses=[],
            )

    scraper = EmptyScraper("https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE")
    book = Book(id=69, book_order=3, book_key="LEV", abbreviation="레", name="레위기")

    try:
        process_book(repo=repo, conn=conn, scraper=scraper, book=book)
    except RuntimeError as exc:
        assert "Parsed 0 verses" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    # Chapter 2 is missing from the map, but nothing was written or committed.
    assert repo.inserted_chapters == []
    assert conn.commits == 0


BIBLEGATEWAY_WEB_ENTRY_URL = "https://www.biblegateway.com/passage/?search=Genesis%201&version=WEB"

WEB_TRANSLATION_METADATA = {
    "id": 3,
    "language_code": "en",
    "name": "World English Bible",
    "translation_type": "WEB",
}

# Derived from the source of truth so a newly supported translation cannot leak
# between tests: a hardcoded list silently missed ASV_ENTRY_URL once already.
ENTRY_URL_ENV_KEYS = tuple(ENTRY_URL_ENV_BY_TRANSLATION_TYPE.values()) + (
    "BIBLE_TRANSLATION_ID",
    "BIBLE_TRANSLATION_TYPE",
    "BIBLE_TRANSLATION_NAME",
    "BIBLE_LANGUAGE_CODE",
)


class BibleGatewayScraper(FakeScraper):
    def get_source_name(self) -> str:
        return "biblegateway"

    def _get_biblegateway_book_name(self, book_order: int) -> str | None:
        return {1: "Genesis", 9: "1 Samuel"}.get(book_order)


def _with_entry_url_env(overrides: dict[str, str]):
    """Context helper: apply env overrides, clearing every entry-url related key first."""

    class _Scope:
        def __enter__(self) -> None:
            self.original = {key: os.getenv(key) for key in ENTRY_URL_ENV_KEYS}
            for key in ENTRY_URL_ENV_KEYS:
                os.environ.pop(key, None)
            os.environ.update(overrides)

        def __exit__(self, *_exc: object) -> None:
            for key, value in self.original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return _Scope()


def test_resolve_default_entry_url_uses_web_entry_url_when_only_one_configured() -> None:
    with _with_entry_url_env({"WEB_ENTRY_URL": BIBLEGATEWAY_WEB_ENTRY_URL}):
        assert resolve_default_entry_url() == BIBLEGATEWAY_WEB_ENTRY_URL


def test_resolve_default_entry_url_prefers_web_when_translation_type_is_web() -> None:
    with _with_entry_url_env(
        {
            "KJV_ENTRY_URL": "https://thekingsbible.com/Bible/1/1",
            "WEB_ENTRY_URL": BIBLEGATEWAY_WEB_ENTRY_URL,
            "BIBLE_TRANSLATION_TYPE": "WEB",
        }
    ):
        assert resolve_default_entry_url() == BIBLEGATEWAY_WEB_ENTRY_URL


def test_resolve_default_entry_url_rejects_ambiguous_english_sources() -> None:
    with _with_entry_url_env(
        {
            "KJV_ENTRY_URL": "https://thekingsbible.com/Bible/1/1",
            "WEB_ENTRY_URL": BIBLEGATEWAY_WEB_ENTRY_URL,
            "BIBLE_LANGUAGE_CODE": "en",
        }
    ):
        try:
            resolve_default_entry_url()
        except ValueError as exc:
            assert "Ambiguous entry URL" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_resolve_default_entry_url_keeps_kjv_behaviour_without_web_entry_url() -> None:
    with _with_entry_url_env(
        {
            "KJV_ENTRY_URL": "https://thekingsbible.com/Bible/1/1",
            "NKRV_ENTRY_URL": "https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE",
            "BIBLE_LANGUAGE_CODE": "en",
        }
    ):
        assert resolve_default_entry_url() == "https://thekingsbible.com/Bible/1/1"


def test_validate_source_translation_compatibility_for_biblegateway_web() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(WEB_TRANSLATION_METADATA)
    scraper = BibleGatewayScraper(BIBLEGATEWAY_WEB_ENTRY_URL)

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_rejects_biblegateway_with_kjv() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = {
        "id": 10,
        "language_code": "en",
        "name": "King James Version",
        "translation_type": "KJV",
    }
    scraper = BibleGatewayScraper(BIBLEGATEWAY_WEB_ENTRY_URL)

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_rejects_thekingsbible_with_web() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(WEB_TRANSLATION_METADATA)

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


BIBLEGATEWAY_ASV_ENTRY_URL = "https://www.biblegateway.com/passage/?search=Genesis%201&version=ASV"

ASV_TRANSLATION_METADATA = {
    "id": 23,
    "language_code": "en",
    "name": "American Standard Version",
    "translation_type": "ASV",
}


def test_resolve_default_entry_url_uses_asv_entry_url_when_only_one_configured() -> None:
    with _with_entry_url_env({"ASV_ENTRY_URL": BIBLEGATEWAY_ASV_ENTRY_URL}):
        assert resolve_default_entry_url() == BIBLEGATEWAY_ASV_ENTRY_URL


def test_resolve_default_entry_url_prefers_asv_when_translation_type_is_asv() -> None:
    with _with_entry_url_env(
        {
            "KJV_ENTRY_URL": "https://thekingsbible.com/Bible/1/1",
            "WEB_ENTRY_URL": BIBLEGATEWAY_WEB_ENTRY_URL,
            "ASV_ENTRY_URL": BIBLEGATEWAY_ASV_ENTRY_URL,
            "BIBLE_TRANSLATION_TYPE": "ASV",
        }
    ):
        assert resolve_default_entry_url() == BIBLEGATEWAY_ASV_ENTRY_URL


def test_resolve_default_entry_url_rejects_three_way_english_ambiguity() -> None:
    with _with_entry_url_env(
        {
            "KJV_ENTRY_URL": "https://thekingsbible.com/Bible/1/1",
            "WEB_ENTRY_URL": BIBLEGATEWAY_WEB_ENTRY_URL,
            "ASV_ENTRY_URL": BIBLEGATEWAY_ASV_ENTRY_URL,
            "BIBLE_LANGUAGE_CODE": "en",
        }
    ):
        try:
            resolve_default_entry_url()
        except ValueError as exc:
            assert "Ambiguous entry URL" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_validate_source_translation_compatibility_for_biblegateway_asv() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(ASV_TRANSLATION_METADATA)
    scraper = BibleGatewayScraper(BIBLEGATEWAY_ASV_ENTRY_URL)

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_rejects_asv_source_with_web_metadata() -> None:
    # The ASV entry URL must not load into the WEB translation.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(WEB_TRANSLATION_METADATA)
    scraper = BibleGatewayScraper(BIBLEGATEWAY_ASV_ENTRY_URL)

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_rejects_thekingsbible_with_asv() -> None:
    # Reachable in practice: BIBLE_TRANSLATION_ID alone does not steer the entry URL,
    # so an ASV run can silently fall back to the KJV source.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(ASV_TRANSLATION_METADATA)

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


def test_validate_source_translation_compatibility_rejects_bskorea_with_asv() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(ASV_TRANSLATION_METADATA)
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


def test_validate_source_translation_compatibility_rejects_unmapped_version_with_web() -> None:
    # A biglegateway version outside the table must not accept WEB metadata.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(WEB_TRANSLATION_METADATA)
    scraper = BibleGatewayScraper(
        "https://www.biblegateway.com/passage/?search=Genesis%201&version=KJ21"
    )

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


EBIBLE_RV1909_ENTRY_URL = "https://ebible.org/spaRV1909/GEN01.htm"
EBIBLE_SBLM_ENTRY_URL = "https://ebible.org/spablm/GEN01.htm"
EBIBLE_JPNMEB_ENTRY_URL = "https://ebible.org/jpnm/GEN01.htm"

RVR1909_TRANSLATION_METADATA = {
    "id": 29,
    "language_code": "es",
    "name": "Reina Valera 1909",
    "translation_type": "RVR1909",
}

JPNMEB_TRANSLATION_METADATA = {
    "id": 36,
    "language_code": "ja",
    "name": "フリーダム・バイブル",
    "translation_type": "JPNMEB",
}

SBLM_TRANSLATION_METADATA = {
    "id": 34,
    "language_code": "es",
    "name": "Santa Biblia libre para el mundo",
    "translation_type": "SBLM",
}


class EbibleScraper(FakeScraper):
    def get_source_name(self) -> str:
        return "ebible"


def test_resolve_default_entry_url_uses_rvr1909_when_only_one_configured() -> None:
    with _with_entry_url_env({"RVR1909_ENTRY_URL": EBIBLE_RV1909_ENTRY_URL}):
        assert resolve_default_entry_url() == EBIBLE_RV1909_ENTRY_URL


def test_resolve_default_entry_url_selects_rvr1909_by_spanish_language_code() -> None:
    with _with_entry_url_env(
        {
            "KJV_ENTRY_URL": "https://thekingsbible.com/Bible/1/1",
            "RVR1909_ENTRY_URL": EBIBLE_RV1909_ENTRY_URL,
            "BIBLE_LANGUAGE_CODE": "es",
        }
    ):
        assert resolve_default_entry_url() == EBIBLE_RV1909_ENTRY_URL


def test_validate_source_translation_compatibility_for_ebible_rvr1909() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(RVR1909_TRANSLATION_METADATA)
    scraper = EbibleScraper(EBIBLE_RV1909_ENTRY_URL)

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_for_ebible_sblm() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(SBLM_TRANSLATION_METADATA)
    scraper = EbibleScraper(EBIBLE_SBLM_ENTRY_URL)

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_rejects_sblm_url_with_rvr1909_metadata() -> None:
    # eBible serves both translations, so the source name alone cannot tell them apart.
    # Without the path-derived version token this mismatch would pass silently and load
    # SBLM text under the RV1909 books.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(RVR1909_TRANSLATION_METADATA)
    scraper = EbibleScraper(EBIBLE_SBLM_ENTRY_URL)

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_rejects_rvr1909_url_with_sblm_metadata() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(SBLM_TRANSLATION_METADATA)
    scraper = EbibleScraper(EBIBLE_RV1909_ENTRY_URL)

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_ignores_ebible_code_case() -> None:
    # The RV1909 code is mixed case; a differently-cased URL must still resolve.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(RVR1909_TRANSLATION_METADATA)
    scraper = EbibleScraper("https://ebible.org/sparv1909/GEN01.htm")

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_resolve_default_entry_url_is_ambiguous_for_two_spanish_sources() -> None:
    with _with_entry_url_env({
        "RVR1909_ENTRY_URL": EBIBLE_RV1909_ENTRY_URL,
        "SBLM_ENTRY_URL": EBIBLE_SBLM_ENTRY_URL,
        "BIBLE_LANGUAGE_CODE": "es",
    }):
        try:
            resolve_default_entry_url()
        except ValueError as exc:
            assert "Ambiguous entry URL" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_resolve_default_entry_url_picks_sblm_when_translation_type_declared() -> None:
    with _with_entry_url_env({
        "RVR1909_ENTRY_URL": EBIBLE_RV1909_ENTRY_URL,
        "SBLM_ENTRY_URL": EBIBLE_SBLM_ENTRY_URL,
        "BIBLE_LANGUAGE_CODE": "es",
        "BIBLE_TRANSLATION_TYPE": "SBLM",
    }):
        assert resolve_default_entry_url() == EBIBLE_SBLM_ENTRY_URL


def test_validate_source_translation_compatibility_for_ebible_jfb() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(JPNMEB_TRANSLATION_METADATA)
    scraper = EbibleScraper(EBIBLE_JPNMEB_ENTRY_URL)

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_separates_three_ebible_translations() -> None:
    """eBible now serves three translations, so the path token has to tell them apart."""
    pairs = [
        (EBIBLE_JPNMEB_ENTRY_URL, SBLM_TRANSLATION_METADATA),
        (EBIBLE_JPNMEB_ENTRY_URL, RVR1909_TRANSLATION_METADATA),
        (EBIBLE_SBLM_ENTRY_URL, JPNMEB_TRANSLATION_METADATA),
        (EBIBLE_RV1909_ENTRY_URL, JPNMEB_TRANSLATION_METADATA),
    ]
    for entry_url, metadata in pairs:
        repo = FakeRepo()
        conn = FakeConn()
        conn.translation_metadata = dict(metadata)
        scraper = EbibleScraper(entry_url)
        try:
            validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
        except RuntimeError as exc:
            assert "Source/translation mismatch" in str(exc)
        else:
            raise AssertionError(f"expected RuntimeError for {entry_url} + {metadata['translation_type']}")


EBIBLE_LSG1910_ENTRY_URL = "https://ebible.org/fraLSG/GEN01.htm"

LSG1910_TRANSLATION_METADATA = {
    "id": 42,
    "language_code": "fr",
    "name": "Louis Segond 1910",
    "translation_type": "LSG1910",
}


def test_validate_source_translation_compatibility_for_ebible_lsg1910() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(LSG1910_TRANSLATION_METADATA)
    scraper = EbibleScraper(EBIBLE_LSG1910_ENTRY_URL)

    validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)


def test_validate_source_translation_compatibility_recognises_lsg1910_by_name() -> None:
    # With translation_type empty the row is identified by (name, language_code), so the
    # registered name has to match the bible_translation row character for character.
    # An unrecognised name only logs a warning, so the rejection is what proves the match.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(LSG1910_TRANSLATION_METADATA, translation_type=None)
    scraper = EbibleScraper(EBIBLE_RV1909_ENTRY_URL)

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "identifies 'LSG1910'" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_separates_lsg1910_from_other_ebible_translations() -> None:
    """A fourth eBible translation: fraLSG must pass for none of the other three, and
    none of them for LSG1910."""
    pairs = [
        (EBIBLE_LSG1910_ENTRY_URL, RVR1909_TRANSLATION_METADATA),
        (EBIBLE_LSG1910_ENTRY_URL, SBLM_TRANSLATION_METADATA),
        (EBIBLE_LSG1910_ENTRY_URL, JPNMEB_TRANSLATION_METADATA),
        (EBIBLE_RV1909_ENTRY_URL, LSG1910_TRANSLATION_METADATA),
        (EBIBLE_SBLM_ENTRY_URL, LSG1910_TRANSLATION_METADATA),
        (EBIBLE_JPNMEB_ENTRY_URL, LSG1910_TRANSLATION_METADATA),
    ]
    for entry_url, metadata in pairs:
        repo = FakeRepo()
        conn = FakeConn()
        conn.translation_metadata = dict(metadata)
        scraper = EbibleScraper(entry_url)
        try:
            validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
        except RuntimeError as exc:
            assert "Source/translation mismatch" in str(exc)
        else:
            raise AssertionError(f"expected RuntimeError for {entry_url} + {metadata['translation_type']}")


def test_resolve_default_entry_url_picks_lsg1910_for_french() -> None:
    with _with_entry_url_env({
        "LSG1910_ENTRY_URL": EBIBLE_LSG1910_ENTRY_URL,
        "SBLM_ENTRY_URL": EBIBLE_SBLM_ENTRY_URL,
        "BIBLE_LANGUAGE_CODE": "fr",
    }):
        assert resolve_default_entry_url() == EBIBLE_LSG1910_ENTRY_URL


def test_resolve_default_entry_url_picks_jfb_for_japanese() -> None:
    with _with_entry_url_env({
        "JPNMEB_ENTRY_URL": EBIBLE_JPNMEB_ENTRY_URL,
        "SBLM_ENTRY_URL": EBIBLE_SBLM_ENTRY_URL,
        "BIBLE_LANGUAGE_CODE": "ja",
    }):
        assert resolve_default_entry_url() == EBIBLE_JPNMEB_ENTRY_URL


def test_validate_source_translation_compatibility_rejects_ebible_with_rvr1960() -> None:
    # RVR1960 already exists in the DB; loading 1909 text under it would be silent
    # corruption, so the check must refuse it.
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = {
        "id": 28,
        "language_code": "es",
        "name": "Reina-Valera 1960",
        "translation_type": "RVR1960",
    }
    scraper = EbibleScraper(EBIBLE_RV1909_ENTRY_URL)

    try:
        validate_source_translation_compatibility(repo=repo, conn=conn, scraper=scraper)
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_validate_source_translation_compatibility_rejects_thekingsbible_with_rvr1909() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = dict(RVR1909_TRANSLATION_METADATA)

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


def test_resolve_book_code_for_source_uses_book_name_for_biblegateway() -> None:
    scraper = BibleGatewayScraper(BIBLEGATEWAY_WEB_ENTRY_URL)
    book = Book(
        id=75,
        book_order=9,
        book_key="1SA",
        abbreviation="1Sam",
        name="1 Samuel",
    )

    assert resolve_book_code_for_source(scraper, book) == "1 Samuel"


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


class _RowCursor:
    """Minimal psycopg2-like cursor returning a fixed row set."""

    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows
        self.executed: list[tuple] = []

    def __enter__(self) -> "_RowCursor":
        return self

    def __exit__(self, *_exc) -> bool:
        return False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[tuple]:
        return self._rows


class _RowConn:
    def __init__(self, rows: list[tuple]) -> None:
        self.cursor_obj = _RowCursor(rows)

    def cursor(self) -> _RowCursor:
        return self.cursor_obj


def test_get_verse_texts_maps_verse_number_to_text() -> None:
    from db import BibleRepository

    conn = _RowConn([(2, "segundo"), (1, "primero"), (3, "tercero")])
    repo = BibleRepository(translation_id=33)

    assert repo.get_verse_texts(conn, 4242) == {
        1: "primero",
        2: "segundo",
        3: "tercero",
    }
    _query, params = conn.cursor_obj.executed[0]
    assert params == (4242,)


def test_get_verse_texts_returns_empty_dict_for_empty_chapter() -> None:
    from db import BibleRepository

    repo = BibleRepository(translation_id=33)
    assert repo.get_verse_texts(_RowConn([]), 1) == {}


def _with_env(**values):
    """Set env vars for the duration of a call and restore them afterwards."""
    original = {key: os.getenv(key) for key in values}

    def restore() -> None:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    for key, value in values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return restore


def test_resolve_default_entry_url_rejects_ambiguous_japanese() -> None:
    # 'ja' now covers two translations, so the language code alone no longer identifies
    # a source - the same trap 'en' has. Raising beats silently loading the wrong text.
    restore = _with_env(
        JPNMEB_ENTRY_URL="https://ebible.org/jpnm/GEN01.htm",
        KOUGO_ENTRY_URL="https://jpn.bible/kougo/gen#1",
        BIBLE_LANGUAGE_CODE="ja",
        BIBLE_TRANSLATION_TYPE=None,
        BIBLE_TRANSLATION_ID=None,
        BIBLE_TRANSLATION_NAME=None,
        KJV_ENTRY_URL=None,
        NKRV_ENTRY_URL=None,
        WEB_ENTRY_URL=None,
        ASV_ENTRY_URL=None,
        RVR1909_ENTRY_URL=None,
        SBLM_ENTRY_URL=None,
    )
    try:
        try:
            resolve_default_entry_url()
        except ValueError as exc:
            assert "Ambiguous entry URL" in str(exc)
            assert "JPNMEB_ENTRY_URL" in str(exc)
            assert "KOUGO_ENTRY_URL" in str(exc)
        else:
            raise AssertionError("expected ValueError")
    finally:
        restore()


def test_resolve_default_entry_url_keeps_jpnmeb_when_type_is_declared() -> None:
    restore = _with_env(
        JPNMEB_ENTRY_URL="https://ebible.org/jpnm/GEN01.htm",
        KOUGO_ENTRY_URL="https://jpn.bible/kougo/gen#1",
        BIBLE_LANGUAGE_CODE="ja",
        BIBLE_TRANSLATION_TYPE="JPNMEB",
        BIBLE_TRANSLATION_ID=None,
        BIBLE_TRANSLATION_NAME=None,
        KJV_ENTRY_URL=None,
        NKRV_ENTRY_URL=None,
        WEB_ENTRY_URL=None,
        ASV_ENTRY_URL=None,
        RVR1909_ENTRY_URL=None,
        SBLM_ENTRY_URL=None,
    )
    try:
        assert resolve_default_entry_url() == "https://ebible.org/jpnm/GEN01.htm"
    finally:
        restore()


def test_resolve_default_entry_url_selects_kougo_when_type_is_declared() -> None:
    restore = _with_env(
        JPNMEB_ENTRY_URL="https://ebible.org/jpnm/GEN01.htm",
        KOUGO_ENTRY_URL="https://jpn.bible/kougo/gen#1",
        BIBLE_LANGUAGE_CODE="ja",
        BIBLE_TRANSLATION_TYPE="KOUGO",
        BIBLE_TRANSLATION_ID=None,
        BIBLE_TRANSLATION_NAME=None,
        KJV_ENTRY_URL=None,
        NKRV_ENTRY_URL=None,
        WEB_ENTRY_URL=None,
        ASV_ENTRY_URL=None,
        RVR1909_ENTRY_URL=None,
        SBLM_ENTRY_URL=None,
    )
    try:
        assert resolve_default_entry_url() == "https://jpn.bible/kougo/gen#1"
    finally:
        restore()


def test_validate_source_translation_compatibility_for_jpnbible_kougo() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = {
        "id": 37,
        "language_code": "ja",
        "name": "口語訳聖書",
        "translation_type": "KOUGO",
    }

    class JpnBibleScraper(FakeScraper):
        def get_source_name(self) -> str:
            return "jpnbible"

    validate_source_translation_compatibility(
        repo=repo, conn=conn, scraper=JpnBibleScraper("https://jpn.bible/kougo/gen#1")
    )


def test_validate_source_translation_compatibility_rejects_jpnbible_with_jpnmeb() -> None:
    repo = FakeRepo()
    conn = FakeConn()
    conn.translation_metadata = {
        "id": 36,
        "language_code": "ja",
        "name": "フリーダム・バイブル",
        "translation_type": "JPNMEB",
    }

    class JpnBibleScraper(FakeScraper):
        def get_source_name(self) -> str:
            return "jpnbible"

    try:
        validate_source_translation_compatibility(
            repo=repo, conn=conn, scraper=JpnBibleScraper("https://jpn.bible/kougo/gen#1")
        )
    except RuntimeError as exc:
        assert "Source/translation mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_resolve_book_code_for_source_is_none_for_jpnbible() -> None:
    class JpnBibleScraper(FakeScraper):
        def get_source_name(self) -> str:
            return "jpnbible"

    scraper = JpnBibleScraper("https://jpn.bible/kougo/gen#1")
    book = Book(id=1, book_order=22, book_key="SNG", name="雅歌", abbreviation="SNG")

    # book_key would build /kougo/sng, which is a 404: the slug table must win.
    assert resolve_book_code_for_source(scraper, book) is None
