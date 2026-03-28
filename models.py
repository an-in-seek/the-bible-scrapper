from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Book:
    """Book row loaded from bible_book."""

    id: int
    book_order: int
    book_key: str
    name: str
    abbreviation: str


@dataclass(slots=True)
class Verse:
    """Parsed verse payload."""

    verse_number: int
    text: str


@dataclass(slots=True)
class ChapterPayload:
    """Parsed chapter payload from source page."""

    book_order: int
    chapter_number: int
    source_url: str
    verses: list[Verse]
