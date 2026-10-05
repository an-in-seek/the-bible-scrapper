import importlib.util
import io
import json
from pathlib import Path

from models import Book, ChapterPayload, Verse

_SPEC = importlib.util.spec_from_file_location(
    "check_translation_drift",
    Path(__file__).resolve().parent.parent / "scripts" / "check_translation_drift.py",
)
drift = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(drift)


class RecordingConn:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def rollback(self) -> None:
        self.events.append("rollback")


class FakeRepo:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def get_chapter_map(self, conn, book_id: int) -> dict[int, int]:
        self.events.append("read chapters")
        return {1: 101, 2: 102}

    def get_verse_texts(self, conn, chapter_id: int) -> dict[int, str]:
        self.events.append(f"read verses {chapter_id}")
        return {1: "same", 2: "stored text"}


class FakeScraper:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def discover_chapter_urls_for_book(self, book_order: int, book_code=None) -> dict[int, str]:
        return {}

    def fetch_chapter_payload(self, book_order, chapter_number, url, book_code=None) -> ChapterPayload:
        self.events.append(f"fetch {chapter_number}")
        return ChapterPayload(
            book_order=book_order,
            chapter_number=chapter_number,
            source_url="",
            verses=[Verse(verse_number=1, text="same"), Verse(verse_number=2, text="source text")],
        )


def _run_compare_book(monkeypatch, output=None, max_report: int = 40):
    monkeypatch.setattr(drift, "resolve_book_code_for_source", lambda scraper, book: None)
    events: list[str] = []
    book = Book(id=7, book_order=22, book_key="SNG", name="Song", abbreviation="Sng")
    result = drift.compare_book(
        FakeScraper(events), FakeRepo(events), RecordingConn(events), book, max_report, 0, output
    )
    return events, result


def test_compare_book_ends_each_read_before_the_page_fetch(monkeypatch) -> None:
    # A run lasts hours behind a transaction-mode pooler; a read left open across the
    # crawl-delayed fetch would pin a backend and block DDL for the whole run.
    events, _ = _run_compare_book(monkeypatch)

    assert events == [
        "read chapters", "rollback",
        "read verses 101", "rollback", "fetch 1",
        "read verses 102", "rollback", "fetch 2",
    ]


def test_compare_book_writes_every_difference_past_max_report(monkeypatch) -> None:
    output = io.StringIO()

    _, (compared, drifted, reported) = _run_compare_book(monkeypatch, output=output, max_report=1)

    rows = [json.loads(line) for line in output.getvalue().splitlines()]
    assert (compared, drifted, reported) == (4, 2, 1)
    assert rows == [
        {"book": 22, "chapter": 1, "verse": 2, "db": "stored text", "source": "source text"},
        {"book": 22, "chapter": 2, "verse": 2, "db": "stored text", "source": "source text"},
    ]
