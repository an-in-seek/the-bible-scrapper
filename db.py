from __future__ import annotations

import os
from typing import Optional

import psycopg2
from psycopg2.extensions import connection

from models import Book, Verse


# Performance recommendation for large volume queries/inserts:
# CREATE INDEX idx_chapter_book_id ON bible_chapter(book_id);
# CREATE INDEX idx_verse_chapter_id ON bible_verse(chapter_id);


class BibleRepository:
    """Repository for bible_book / bible_chapter / bible_verse tables."""

    LEGACY_DEFAULT_TRANSLATION_ID = 10

    def __init__(
        self,
        translation_id: int | None = None,
        translation_type: str | None = None,
        translation_name: str | None = None,
        language_code: str | None = None,
    ) -> None:
        self.translation_id = translation_id or _get_optional_int_env("BIBLE_TRANSLATION_ID")
        self.translation_type = translation_type or os.getenv("BIBLE_TRANSLATION_TYPE")
        self.translation_name = translation_name or os.getenv("BIBLE_TRANSLATION_NAME")
        self.language_code = language_code or os.getenv("BIBLE_LANGUAGE_CODE")
        self._resolved_translation_id: int | None = None
        self._resolved_translation_metadata: dict[str, object] | None = None

    def _get_translation_id(self, conn: connection) -> int:
        if self._resolved_translation_id is not None:
            return self._resolved_translation_id

        if self.translation_id is not None:
            self._resolved_translation_id = self.translation_id
            return self._resolved_translation_id

        clauses: list[str] = []
        params: list[object] = []
        if self.translation_type:
            clauses.append("translation_type = %s")
            params.append(self.translation_type)
        if self.translation_name:
            clauses.append('"name" = %s')
            params.append(self.translation_name)
        if self.language_code:
            clauses.append("language_code = %s")
            params.append(self.language_code)

        if clauses:
            query = f"""
                SELECT id
                FROM public.bible_translation
                WHERE {" AND ".join(clauses)}
                ORDER BY id ASC
                LIMIT 1
            """
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                row = cur.fetchone()
            if row and row[0] is not None:
                self._resolved_translation_id = row[0]
                return self._resolved_translation_id
            raise RuntimeError(
                "Could not resolve bible_translation.id for the configured "
                "BIBLE_TRANSLATION_TYPE/BIBLE_TRANSLATION_NAME/BIBLE_LANGUAGE_CODE"
            )

        self._resolved_translation_id = self.LEGACY_DEFAULT_TRANSLATION_ID
        return self._resolved_translation_id

    def fetch_books(
        self,
        conn: connection,
        start_book: int = 1,
        end_book: int = 66,
    ) -> list[Book]:
        translation_id = self._get_translation_id(conn)
        query = """
            SELECT id, book_order, book_key, name, abbreviation
            FROM public.bible_book
            WHERE translation_id = %s
              AND book_order BETWEEN %s AND %s
            ORDER BY book_order ASC
        """
        with conn.cursor() as cur:
            cur.execute(query, (translation_id, start_book, end_book))
            rows = cur.fetchall()

        return [
            Book(
                id=row[0],
                book_order=row[1],
                book_key=row[2],
                name=row[3],
                abbreviation=row[4],
            )
            for row in rows
        ]

    def get_translation_metadata(self, conn: connection) -> dict[str, object]:
        if self._resolved_translation_metadata is not None:
            return self._resolved_translation_metadata

        translation_id = self._get_translation_id(conn)
        query = """
            SELECT id, language_code, "name", translation_type
            FROM public.bible_translation
            WHERE id = %s
        """
        with conn.cursor() as cur:
            cur.execute(query, (translation_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError(f"Could not load bible_translation metadata for id={translation_id}")

        self._resolved_translation_metadata = {
            "id": row[0],
            "language_code": row[1],
            "name": row[2],
            "translation_type": row[3],
        }
        return self._resolved_translation_metadata

    def get_last_completed_book_order(self, conn: connection) -> Optional[int]:
        """Returns max book_order that already has at least one verse."""
        translation_id = self._get_translation_id(conn)
        query = """
            SELECT MAX(b.book_order)
            FROM public.bible_book b
            WHERE b.translation_id = %s
              AND EXISTS (
                  SELECT 1
                  FROM public.bible_chapter c
                  JOIN public.bible_verse v ON v.chapter_id = c.id
                  WHERE c.book_id = b.id
              )
        """
        with conn.cursor() as cur:
            cur.execute(query, (translation_id,))
            row = cur.fetchone()
        return row[0] if row and row[0] is not None else None

    def get_chapter_map(self, conn: connection, book_id: int) -> dict[int, int]:
        query = """
            SELECT chapter_number, id
            FROM public.bible_chapter
            WHERE book_id = %s
        """
        with conn.cursor() as cur:
            cur.execute(query, (book_id,))
            rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}

    def insert_missing_chapters(
        self,
        conn: connection,
        book_id: int,
        chapter_numbers: list[int],
    ) -> int:
        if not chapter_numbers:
            return 0

        query = """
            INSERT INTO public.bible_chapter (book_id, chapter_number)
            VALUES (%s, %s)
        """
        params = [(book_id, chapter_number) for chapter_number in chapter_numbers]
        with conn.cursor() as cur:
            cur.executemany(query, params)
        return len(params)

    def get_existing_verse_numbers(self, conn: connection, chapter_id: int) -> set[int]:
        query = """
            SELECT verse_number
            FROM public.bible_verse
            WHERE chapter_id = %s
        """
        with conn.cursor() as cur:
            cur.execute(query, (chapter_id,))
            rows = cur.fetchall()
        return {row[0] for row in rows}

    def insert_missing_verses(
        self,
        conn: connection,
        chapter_id: int,
        verses: list[Verse],
    ) -> int:
        if not verses:
            return 0

        query = """
            INSERT INTO public.bible_verse (chapter_id, verse_number, text)
            VALUES (%s, %s, %s)
        """
        params = [(chapter_id, verse.verse_number, verse.text) for verse in verses]
        with conn.cursor() as cur:
            cur.executemany(query, params)
        return len(params)

    def sync_identity_sequences(self, conn: connection) -> None:
        """
        Align identity sequences with current max(id) values.
        This prevents duplicate PK errors when sequences are behind data.
        """
        tables = ("public.bible_chapter", "public.bible_verse")
        with conn.cursor() as cur:
            for table in tables:
                cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
                seq_row = cur.fetchone()
                if not seq_row or not seq_row[0]:
                    continue
                seq_name = seq_row[0]

                cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
                max_id = cur.fetchone()[0]
                # is_called=true means next nextval() returns max_id + 1
                cur.execute("SELECT setval(%s, %s, true)", (seq_name, max_id))


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_optional_int_env(name: str) -> int | None:
    value = os.getenv(name)
    if not value:
        return None
    return int(value)


def get_db_connection() -> connection:
    """Build psycopg2 connection using required env vars."""
    return psycopg2.connect(
        host=_get_required_env("DB_HOST"),
        port=int(_get_required_env("DB_PORT")),
        dbname=_get_required_env("DB_NAME"),
        user=_get_required_env("DB_USER"),
        password=_get_required_env("DB_PASSWORD"),
    )
