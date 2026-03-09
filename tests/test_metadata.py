import logging
import shutil
import sqlite3
from unittest.mock import MagicMock, patch

from sosci.cli.metadata import (merge_move_databases, metadata_update,
                                translate_context_file)

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


def test_metadata_update_multiple_subs(temp_sqlite_db, tmp_path):
    """Multiple substitution rules are all applied in order."""
    out = tmp_path / "obsdb.sqlite"
    metadata_update(
        db=str(temp_sqlite_db),
        outfile=out,
        sub=["/so/:/new_root/", "/data/:/DATA/"],
    )
    con = sqlite3.connect(out)
    rows = con.execute("SELECT path FROM obs ORDER BY obs_id").fetchall()
    con.close()
    assert rows == [("/new_root/DATA/obs_001",), ("/new_root/DATA/obs_002",)]


def test_metadata_update_no_subs_no_output(temp_sqlite_db, tmp_path):
    """Empty sub list prints a warning and creates no output file."""
    out = tmp_path / "obsdb.sqlite"
    metadata_update(db=str(temp_sqlite_db), outfile=out, sub=[])
    assert not out.exists()


# --- merge_move_databases additional cases ---

def test_merge_move_databases_already_in_sync(temp_sqlite_db, tmp_path):
    """Staged DB identical to final → staged deleted, final content unchanged."""
    logger = logging.getLogger("test")
    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db, staged_path / "obsdb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "obsdb.sqlite")

    merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    assert not (staged_path / "obsdb.sqlite").exists()
    con = sqlite3.connect(final_path / "obsdb.sqlite")
    obs_ids = [r[0] for r in con.execute("SELECT obs_id FROM obs ORDER BY obs_id")]
    con.close()
    assert obs_ids == ["obs_001", "obs_002"]


def test_merge_move_databases_unknown_pattern(temp_sqlite_db, tmp_path):
    """DB not matching obsdb/obsfiledb patterns is atomically moved to final (first sync)."""
    logger = logging.getLogger("test")
    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db, staged_path / "somedb.sqlite")
    # No corresponding file in final_path

    merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    assert not (staged_path / "somedb.sqlite").exists()
    assert (final_path / "somedb.sqlite").exists()


def test_merge_move_databases_nested_subdir(temp_sqlite_db, temp_sqlite_db2, tmp_path):
    """Staged DB in a subdirectory is mapped to the correct subdirectory in final."""
    logger = logging.getLogger("test")
    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    (staged_path / "subdir").mkdir(parents=True)
    (final_path / "subdir").mkdir(parents=True)

    shutil.copy(temp_sqlite_db2, staged_path / "subdir" / "obsdb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "subdir" / "obsdb.sqlite")

    merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    assert not (staged_path / "subdir" / "obsdb.sqlite").exists()
    assert (final_path / "subdir" / "obsdb.sqlite").exists()
    con = sqlite3.connect(final_path / "subdir" / "obsdb.sqlite")
    obs_ids = [r[0] for r in con.execute("SELECT obs_id FROM obs ORDER BY obs_id")]
    con.close()
    # Replaced with temp_sqlite_db2 rows (obs_003, obs_004)
    assert obs_ids == ["obs_003", "obs_004"]


def test_merge_move_databases_obsfiledb_in_sync(temp_sqlite_db, tmp_path):
    """obsfiledb branch: identical DBs → staged deleted, final untouched."""
    logger = logging.getLogger("test")
    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db, staged_path / "obsfiledb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "obsfiledb.sqlite")

    with patch("sosci.cli.metadata.obsfiledb") as mock_obsfiledb:
        mock_obsfiledb.ObsFileDb.return_value = MagicMock()
        mock_obsfiledb.diff_obsfiledbs.return_value = {"different": False}
        merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    assert not (staged_path / "obsfiledb.sqlite").exists()
    assert (final_path / "obsfiledb.sqlite").exists()


def test_merge_move_databases_obsfiledb_patchable(temp_sqlite_db, tmp_path):
    """obsfiledb branch: patchable → patch applied, staged deleted."""
    logger = logging.getLogger("test")
    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db, staged_path / "obsfiledb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "obsfiledb.sqlite")

    mock_target = MagicMock()
    with patch("sosci.cli.metadata.obsfiledb") as mock_obsfiledb:
        mock_obsfiledb.ObsFileDb.return_value = mock_target
        mock_obsfiledb.diff_obsfiledbs.return_value = {
            "different": True,
            "patchable": True,
            "patch_data": {"add": [], "remove": []},
        }
        merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)
        mock_obsfiledb.patch_obsfiledb.assert_called_once()

    assert not (staged_path / "obsfiledb.sqlite").exists()


def test_merge_move_databases_obsfiledb_unpatchable(temp_sqlite_db, tmp_path):
    """obsfiledb branch: unpatchable → staged atomically replaces final."""
    logger = logging.getLogger("test")
    staged_path = tmp_path / "staging"
    final_path = tmp_path / "final"
    staged_path.mkdir()
    final_path.mkdir()

    shutil.copy(temp_sqlite_db, staged_path / "obsfiledb.sqlite")
    shutil.copy(temp_sqlite_db, final_path / "obsfiledb.sqlite")

    with patch("sosci.cli.metadata.obsfiledb") as mock_obsfiledb:
        mock_obsfiledb.ObsFileDb.return_value = MagicMock()
        mock_obsfiledb.diff_obsfiledbs.return_value = {
            "different": True,
            "patchable": False,
            "unpatchable_reason": "schema mismatch",
            "detail": "columns differ",
        }
        merge_move_databases(staged_path=staged_path, final_path=final_path, logger=logger)

    assert not (staged_path / "obsfiledb.sqlite").exists()
    assert (final_path / "obsfiledb.sqlite").exists()


# --- translate_context_file ---

def test_translate_context_file_so_path(tmp_path):
    """/so/ in a line is replaced with destination_path.parent/."""
    ctx = tmp_path / "context.yaml"
    out = tmp_path / "context_local.yaml"
    destination = tmp_path / "dest"

    ctx.write_text("path: /so/data/obs\n")
    translate_context_file(str(ctx), str(out), destination)

    content = out.read_text()
    assert f"{destination.parent}/data/obs" in content
    assert "/so/" not in content


def test_translate_context_file_sqlite_renamed(tmp_path):
    """.sqlite in a line becomes _local.sqlite."""
    ctx = tmp_path / "context.yaml"
    out = tmp_path / "context_local.yaml"
    destination = tmp_path / "dest"

    ctx.write_text("metadata: obsdb.sqlite\n")
    translate_context_file(str(ctx), str(out), destination)

    assert "obsdb_local.sqlite" in out.read_text()


def test_translate_context_file_passthrough(tmp_path):
    """Lines with neither /so/ nor .sqlite pass through unchanged."""
    ctx = tmp_path / "context.yaml"
    out = tmp_path / "context_local.yaml"
    destination = tmp_path / "dest"

    ctx.write_text("name: my_observation\n")
    translate_context_file(str(ctx), str(out), destination)

    assert out.read_text() == "name: my_observation\n"


def test_translate_context_file_mixed_lines(tmp_path):
    """Each line is handled independently: /so/ line, .sqlite line, plain line."""
    ctx = tmp_path / "context.yaml"
    out = tmp_path / "context_local.yaml"
    destination = tmp_path / "dest"

    ctx.write_text(
        "obs_path: /so/data/obs_001\n"
        "db: obsdb.sqlite\n"
        "label: test\n"
    )
    translate_context_file(str(ctx), str(out), destination)

    lines = out.read_text().splitlines()
    assert f"{destination.parent}/data/obs_001" in lines[0]
    assert "obsdb_local.sqlite" in lines[1]
    assert lines[2] == "label: test"
