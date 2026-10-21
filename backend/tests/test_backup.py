import sqlite3

import pytest
from sqlalchemy import create_engine, inspect

from app.backup import snapshot_database
from app.database import Base


def test_snapshot_includes_wal_and_can_bootstrap_again(tmp_path):
    source, backup = tmp_path / "live.db", tmp_path / "snapshot.db"
    engine = create_engine("sqlite:///" + str(source))
    Base.metadata.create_all(engine)
    engine.dispose()
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE backup_fixture (value TEXT)")
        connection.execute("INSERT INTO backup_fixture VALUES ('saved notes')")
        connection.commit()
        snapshot_database(source, backup)
    with sqlite3.connect(backup) as restored:
        assert restored.execute("SELECT value FROM backup_fixture").fetchone() == ("saved notes",)
        assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    restored_engine = create_engine("sqlite:///" + str(backup))
    Base.metadata.create_all(restored_engine)
    Base.metadata.create_all(restored_engine)
    assert set(Base.metadata.tables) <= set(inspect(restored_engine).get_table_names())
    restored_engine.dispose()


def test_existing_destination_is_never_replaced(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "existing.db"
    sqlite3.connect(source).close()
    target.write_bytes(b"user-owned data")
    with pytest.raises(FileExistsError):
        snapshot_database(source, target)
    assert target.read_bytes() == b"user-owned data"


def test_missing_or_invalid_source_does_not_leave_snapshot(tmp_path):
    source, target = tmp_path / "missing.db", tmp_path / "snapshot.db"
    with pytest.raises(FileNotFoundError):
        snapshot_database(source, target)
    assert not target.exists()
    source.write_bytes(b"not a sqlite database")
    with pytest.raises(sqlite3.DatabaseError):
        snapshot_database(source, target)
    assert not target.exists()
