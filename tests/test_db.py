from db import BibleRepository


class FakeCursor:
    def __init__(self, row=None):
        self.row = row
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row=None):
        self.last_cursor = FakeCursor(row=row)

    def cursor(self):
        return self.last_cursor


def test_repository_uses_explicit_translation_id() -> None:
    repo = BibleRepository(translation_id=2)

    assert repo._get_translation_id(object()) == 2


def test_repository_resolves_translation_id_from_translation_metadata() -> None:
    repo = BibleRepository(
        translation_type="NKRV",
        translation_name="개역개정",
        language_code="ko",
    )
    conn = FakeConnection(row=(2,))

    assert repo._get_translation_id(conn) == 2
    assert "FROM public.bible_translation" in conn.last_cursor.executed[0][0]
    assert conn.last_cursor.executed[0][1] == ("NKRV", "개역개정", "ko")


def test_repository_falls_back_to_legacy_translation_id() -> None:
    repo = BibleRepository()

    assert repo._get_translation_id(object()) == 10
