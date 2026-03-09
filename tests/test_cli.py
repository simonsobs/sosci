from argparse import ArgumentParser

import pytest

from sosci.cli.metadata import get_parser as metadata_get_parser
from sosci.cli.purge import get_parser as purge_get_parser


def _make_parser(get_parser_fn):
    return get_parser_fn(ArgumentParser())


# --- metadata-sync argument parsing ---

def test_metadata_parser_defaults():
    """transfer-method defaults to rsync, dry-run defaults to False."""
    parser = _make_parser(metadata_get_parser)
    args = parser.parse_args(["--source-path", "/src", "--destination-path", "/dst"])
    assert args.transfer_method == "rsync"
    assert args.dry_run is False


def test_metadata_parser_globus():
    """--transfer-method globus is accepted."""
    parser = _make_parser(metadata_get_parser)
    args = parser.parse_args([
        "--source-path", "/src",
        "--destination-path", "/dst",
        "--transfer-method", "globus",
    ])
    assert args.transfer_method == "globus"


def test_metadata_parser_invalid_transfer_method():
    """Unsupported transfer method causes a parse error (SystemExit)."""
    parser = _make_parser(metadata_get_parser)
    with pytest.raises(SystemExit):
        parser.parse_args([
            "--source-path", "/src",
            "--destination-path", "/dst",
            "--transfer-method", "ftp",
        ])


def test_metadata_parser_missing_source():
    """Missing --source-path causes a parse error."""
    parser = _make_parser(metadata_get_parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--destination-path", "/dst"])


def test_metadata_parser_missing_destination():
    """Missing --destination-path causes a parse error."""
    parser = _make_parser(metadata_get_parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--source-path", "/src"])


def test_metadata_parser_dry_run():
    """--dry-run flag sets dry_run to True."""
    parser = _make_parser(metadata_get_parser)
    args = parser.parse_args(["--source-path", "/src", "--destination-path", "/dst", "--dry-run"])
    assert args.dry_run is True


def test_metadata_parser_globus_args():
    """Globus-specific arguments are accepted and stored correctly."""
    parser = _make_parser(metadata_get_parser)
    args = parser.parse_args([
        "--source-path", "/src",
        "--destination-path", "/dst",
        "--transfer-method", "globus",
        "--source-endpoint", "uuid-src",
        "--destination-endpoint", "uuid-dst",
        "--globus-client-id", "client-123",
        "--globus-refresh-token-file", "/tokens.json",
    ])
    assert args.source_endpoint == "uuid-src"
    assert args.destination_endpoint == "uuid-dst"
    assert args.globus_client_id == "client-123"
    assert args.globus_refresh_token_file == "/tokens.json"


# --- metadata-purge argument parsing ---

def test_purge_parser_missing_all_required():
    """Missing both --file and --base-path causes a parse error."""
    parser = _make_parser(purge_get_parser)
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_purge_parser_missing_base_path():
    """Missing --base-path causes a parse error."""
    parser = _make_parser(purge_get_parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--file", "purge.txt"])


def test_purge_parser_missing_file():
    """Missing --file causes a parse error."""
    parser = _make_parser(purge_get_parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--base-path", "/data"])


def test_purge_parser_dry_run_default():
    """dry-run defaults to False."""
    parser = _make_parser(purge_get_parser)
    args = parser.parse_args(["--file", "purge.txt", "--base-path", "/data"])
    assert args.dry_run is False


def test_purge_parser_dry_run_flag():
    """--dry-run sets dry_run to True."""
    parser = _make_parser(purge_get_parser)
    args = parser.parse_args(["--file", "purge.txt", "--base-path", "/data", "--dry-run"])
    assert args.dry_run is True


def test_purge_parser_short_flags():
    """Short flag -f is accepted for --file."""
    parser = _make_parser(purge_get_parser)
    args = parser.parse_args(["-f", "purge.txt", "--base-path", "/data"])
    assert args.file == "purge.txt"
