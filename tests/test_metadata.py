import logging
import shutil
import sqlite3

from sosci.cli.metadata import merge_move_databases, metadata_update

from ._helpers import print_db


def test_merge_move_databases_replace(temp_sqlite_db, temp_sqlite_db2, tmp_path):
    """Staged DB (obs_003-004) atomically replaces the final DB (obs_001-002)."""
    logger = logging.getLogger("test")

    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db2, staged_path / "obsdb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "obsdb.sqlite")

    merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    # Staged file must be consumed
    assert not (staged_path / "obsdb.sqlite").exists()

    # Final DB must now contain the staged rows (obs_003, obs_004)
    expected_rows = [
        ("obs_003", "obs_003.hdf5", "/so/data/obs_003/obs_003.hdf5"),
        ("obs_004", "obs_004.hdf5", "/so/data/obs_004/obs_004.hdf5"),
    ]
    con = sqlite3.connect(final_path / "obsdb.sqlite")
    for expected_row, row in zip(expected_rows, con.execute("SELECT * FROM files")):
        assert expected_row[0] == row[0]
        assert expected_row[1] == row[1]
        assert expected_row[2] == row[2]
    con.close()


def test_merge_move_databases_merge(temp_sqlite_db_combined, temp_sqlite_db, tmp_path):
    """Staged DB (obs_001-004) replaces final DB (obs_001-002); all rows land in final."""
    logger = logging.getLogger("test")

    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db_combined, staged_path / "obsdb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "obsdb.sqlite")

    merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    # Staged file must be consumed
    assert not (staged_path / "obsdb.sqlite").exists()
    # Final DB must now contain all four rows from the combined staged DB
    expected_rows = [
        ('obs_001', 1700000000.0, '/so/data/obs_001'),
        ('obs_002', 1700001000.0, '/so/data/obs_002'),
        ('obs_003', 1700002000.0, '/so/data/obs_003'),
        ('obs_004', 1700003000.0, '/so/data/obs_004'),
    ]
    con = sqlite3.connect(final_path / "obsdb.sqlite")
    for expected_row, row in zip(expected_rows, con.execute("SELECT * FROM obs")):
        assert expected_row[0] == row[0]
        assert expected_row[1] == row[1]
        assert expected_row[2] == row[2]
    con.close()

def test_metadata_update(temp_sqlite_db, temp_sqlite_db2, tmp_path):

    # With sub=[], metadata_update returns early without creating an output file
    out1 = tmp_path / "obsdb.sqlite"
    out2 = tmp_path / "obsdb2.sqlite"
    assert not out1.exists()
    assert not out2.exists()
    metadata_update(db=str(temp_sqlite_db), outfile=out1, sub=[f"/so/:/actual_so_space/"])
    assert out1.exists()

    con = sqlite3.connect(out1)
    expected_rows = [("obs_001", "obs_001.hdf5", "/actual_so_space/data/obs_001/obs_001.hdf5"),
                     ("obs_002", "obs_002.hdf5", "/actual_so_space/data/obs_002/obs_002.hdf5")]
    for expected_row, row in zip(expected_rows, con.execute("SELECT * from files")):
        assert expected_row[0] == row[0]
        assert expected_row[1] == row[1]
        assert expected_row[2] == row[2]
    con.close()

    metadata_update(db=str(temp_sqlite_db2), outfile=out2, sub=[])
    assert not out2.exists()

