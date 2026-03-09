import logging
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from sosci.cli.purge import _main


@pytest.fixture
def purge_args(tmp_path):
    return Namespace(base_path=str(tmp_path), dry_run=False, file=None)


def test_purge_local_file_deletes(tmp_path, purge_args):
    """Files listed in a local purge list are deleted."""
    target = tmp_path / "obs_001.hdf5"
    target.write_text("data")

    purge_list = tmp_path / "purge.txt"
    purge_list.write_text("obs_001.hdf5\n")

    purge_args.file = str(purge_list)
    _main(purge_args, logging.getLogger("test"))

    assert not target.exists()


def test_purge_dry_run_does_not_delete(tmp_path, purge_args):
    """Dry run does not delete files."""
    target = tmp_path / "obs_001.hdf5"
    target.write_text("data")

    purge_list = tmp_path / "purge.txt"
    purge_list.write_text("obs_001.hdf5\n")

    purge_args.file = str(purge_list)
    purge_args.dry_run = True
    _main(purge_args, logging.getLogger("test"))

    assert target.exists()


def test_purge_missing_file_skipped(tmp_path, purge_args):
    """Files listed but absent on disk are silently skipped (no exception)."""
    purge_list = tmp_path / "purge.txt"
    purge_list.write_text("nonexistent.hdf5\n")

    purge_args.file = str(purge_list)
    _main(purge_args, logging.getLogger("test"))  # must not raise


def test_purge_empty_lines_skipped(tmp_path, purge_args):
    """Blank and whitespace-only lines in the purge file are ignored."""
    target = tmp_path / "obs_001.hdf5"
    target.write_text("data")

    purge_list = tmp_path / "purge.txt"
    purge_list.write_text("\n   \nobs_001.hdf5\n\n")

    purge_args.file = str(purge_list)
    _main(purge_args, logging.getLogger("test"))

    assert not target.exists()


def test_purge_multiple_files(tmp_path, purge_args):
    """All files listed in the purge list are deleted."""
    files = [tmp_path / f"obs_00{i}.hdf5" for i in range(1, 4)]
    for f in files:
        f.write_text("data")

    purge_list = tmp_path / "purge.txt"
    purge_list.write_text("\n".join(f.name for f in files))

    purge_args.file = str(purge_list)
    _main(purge_args, logging.getLogger("test"))

    for f in files:
        assert not f.exists()


def test_purge_url(tmp_path, purge_args):
    """Purge list fetched from an allowed GitHub URL; matching files are deleted."""
    target = tmp_path / "obs_001.hdf5"
    target.write_text("data")

    purge_args.file = "https://github.com/simonsobs/sosci/raw/main/purge.txt"

    mock_response = MagicMock()
    mock_response.read.return_value = b"obs_001.hdf5\n"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("sosci.cli.purge.urlopen", return_value=mock_response):
        _main(purge_args, logging.getLogger("test"))

    assert not target.exists()
