import sqlite3

import pytest


@pytest.fixture
def temp_sqlite_db(tmp_path):
    """Create a temporary SQLite database with sample tables for testing."""
    db_path = tmp_path / "test.sqlite"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE obs (obs_id TEXT PRIMARY KEY, timestamp REAL, path TEXT)"
    )
    con.execute(
        "CREATE TABLE files (obs_id TEXT, filename TEXT, path TEXT)"
    )
    con.executemany(
        "INSERT INTO obs VALUES (?, ?, ?)",
        [
            ("obs_001", 1700000000.0, "/so/data/obs_001"),
            ("obs_002", 1700001000.0, "/so/data/obs_002"),
        ],
    )
    con.executemany(
        "INSERT INTO files VALUES (?, ?, ?)",
        [
            ("obs_001", "obs_001.hdf5", "/so/data/obs_001/obs_001.hdf5"),
            ("obs_002", "obs_002.hdf5", "/so/data/obs_002/obs_002.hdf5"),
        ],
    )
    con.commit()
    con.close()
    return db_path

@pytest.fixture
def temp_sqlite_db2(tmp_path_factory):
    tmp_path2 = tmp_path_factory.mktemp("db2")
    """Create a temporary SQLite database with sample tables for testing."""
    db_path = tmp_path2 / "test.sqlite"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE obs (obs_id TEXT PRIMARY KEY, timestamp REAL, path TEXT)"
    )
    con.execute(
        "CREATE TABLE files (obs_id TEXT, filename TEXT, path TEXT)"
    )
    con.executemany(
        "INSERT INTO obs VALUES (?, ?, ?)",
        [
            ("obs_003", 1700000000.0, "/so/data/obs_003"),
            ("obs_004", 1700001000.0, "/so/data/obs_004"),
        ],
    )
    con.executemany(
        "INSERT INTO files VALUES (?, ?, ?)",
        [
            ("obs_003", "obs_003.hdf5", "/so/data/obs_003/obs_003.hdf5"),
            ("obs_004", "obs_004.hdf5", "/so/data/obs_004/obs_004.hdf5"),
        ],
    )
    con.commit()
    con.close()
    return db_path

@pytest.fixture
def temp_sqlite_db_combined(tmp_path_factory):
    """SQLite database containing all four obs (001-004), for merge staging tests."""
    tmp_path3 = tmp_path_factory.mktemp("db_combined")
    db_path = tmp_path3 / "test.sqlite"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE obs (obs_id TEXT PRIMARY KEY, timestamp REAL, path TEXT)"
    )
    con.execute(
        "CREATE TABLE files (obs_id TEXT, filename TEXT, path TEXT)"
    )
    con.executemany(
        "INSERT INTO obs VALUES (?, ?, ?)",
        [
            ("obs_001", 1700000000.0, "/so/data/obs_001"),
            ("obs_002", 1700001000.0, "/so/data/obs_002"),
            ("obs_003", 1700002000.0, "/so/data/obs_003"),
            ("obs_004", 1700003000.0, "/so/data/obs_004"),
        ],
    )
    con.executemany(
        "INSERT INTO files VALUES (?, ?, ?)",
        [
            ("obs_001", "obs_001.hdf5", "/so/data/obs_001/obs_001.hdf5"),
            ("obs_002", "obs_002.hdf5", "/so/data/obs_002/obs_002.hdf5"),
            ("obs_003", "obs_003.hdf5", "/so/data/obs_003/obs_003.hdf5"),
            ("obs_004", "obs_004.hdf5", "/so/data/obs_004/obs_004.hdf5"),
        ],
    )
    con.commit()
    con.close()
    return db_path
