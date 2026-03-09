import logging
from unittest.mock import MagicMock, patch

import pytest

from sosci.transfers.rsync import RsyncTransfer


@pytest.fixture
def logger():
    return logging.getLogger("test")


def _mock_run(returncode=0, stdout="", stderr=""):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_rsync_success(logger):
    """Successful rsync returns True."""
    with patch("subprocess.run", return_value=_mock_run(returncode=0, stdout="sent 100 bytes")) as mock_run:
        transfer = RsyncTransfer(source="/src", destination="/dst", logger=logger)
        assert transfer.transfer() is True
    mock_run.assert_called_once()


def test_rsync_failure(logger):
    """Non-zero returncode returns False."""
    with patch("subprocess.run", return_value=_mock_run(returncode=1, stderr="connection refused")):
        transfer = RsyncTransfer(source="/src", destination="/dst", logger=logger)
        assert transfer.transfer() is False


def test_rsync_dry_run_flag(logger):
    """dry_run=True passes --dry-run to the rsync command."""
    with patch("subprocess.run", return_value=_mock_run()) as mock_run:
        transfer = RsyncTransfer(source="/src", destination="/dst", logger=logger)
        transfer.transfer(dry_run=True)
    cmd = mock_run.call_args[0][0]
    assert "--dry-run" in cmd


def test_rsync_no_dry_run_flag(logger):
    """dry_run=False (default) does not pass --dry-run."""
    with patch("subprocess.run", return_value=_mock_run()) as mock_run:
        transfer = RsyncTransfer(source="/src", destination="/dst", logger=logger)
        transfer.transfer()
    cmd = mock_run.call_args[0][0]
    assert "--dry-run" not in cmd


def test_rsync_source_gets_trailing_slash(logger):
    """Source path without trailing slash has one appended in the command."""
    with patch("subprocess.run", return_value=_mock_run()) as mock_run:
        transfer = RsyncTransfer(source="/src/path", destination="/dst", logger=logger)
        transfer.transfer()
    cmd = mock_run.call_args[0][0]
    src_arg = next(a for a in cmd if a.startswith("/src"))
    assert src_arg == "/src/path/"


def test_rsync_existing_trailing_slash_not_doubled(logger):
    """Source path already ending in / is not double-slashed."""
    with patch("subprocess.run", return_value=_mock_run()) as mock_run:
        transfer = RsyncTransfer(source="/src/path/", destination="/dst", logger=logger)
        transfer.transfer()
    cmd = mock_run.call_args[0][0]
    src_arg = next(a for a in cmd if a.startswith("/src"))
    assert src_arg == "/src/path/"
    assert "//" not in src_arg
