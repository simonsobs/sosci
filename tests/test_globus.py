from unittest.mock import MagicMock, patch

import pytest

from sosci.transfers.globus import GlobusTransfer


@pytest.fixture
def gt(logger):
    with patch("sosci.transfers.globus.globus_sdk") as mock_sdk:
        mock_sdk.NativeAppAuthClient.return_value = MagicMock()
        t = GlobusTransfer(
            source={"path": "/src", "endpoint": "src-uuid", "globus_root_path": "/src"},
            destination={"path": "/dst", "endpoint": "dst-uuid", "globus_root_path": "/dst"},
            globus_config={"client_id": "cid", "refresh_token_file": "/tokens.json"},
            logger=logger,
        )
        yield t, mock_sdk


def test_transfer_submits_and_returns_task_id(gt):
    t, mock_sdk = gt
    transfer_client = MagicMock()
    transfer_client.submit_transfer.return_value = {"task_id": "task-123"}
    mock_sdk.TransferClient.return_value = transfer_client

    with patch.object(t, "_get_authorizer", return_value=MagicMock()):
        task_id = t.transfer(["/src/foo/a.txt", "/src/bar/b.txt"])

    assert task_id == "task-123"
    transfer_client.submit_transfer.assert_called_once()
    td = mock_sdk.TransferData.return_value
    assert td.add_item.call_count == 2


def test_transfer_path_translation(gt):
    t, mock_sdk = gt
    transfer_client = MagicMock()
    transfer_client.submit_transfer.return_value = {"task_id": "x"}
    mock_sdk.TransferClient.return_value = transfer_client
    td = mock_sdk.TransferData.return_value

    with patch.object(t, "_get_authorizer", return_value=MagicMock()):
        t.transfer(["/src/foo/a.txt"])

    # source: /src/foo/a.txt relative to globus_root_path /src → foo/a.txt
    # dest: /dst/foo/a.txt relative to globus_root_path /dst → foo/a.txt
    args, _ = td.add_item.call_args
    assert args[0] == "foo/a.txt"
    assert args[1] == "foo/a.txt"


def test_delete_submits_and_returns_task_id(gt):
    t, mock_sdk = gt
    transfer_client = MagicMock()
    transfer_client.submit_delete.return_value = {"task_id": "del-7"}
    mock_sdk.TransferClient.return_value = transfer_client

    with patch.object(t, "_get_authorizer", return_value=MagicMock()):
        task_id = t.delete(["/src/foo/a.txt"])

    assert task_id == "del-7"
    transfer_client.submit_delete.assert_called_once()
    mock_sdk.DeleteData.return_value.add_item.assert_called_once()


def test_compute_destination_path_valid(gt):
    from pathlib import Path
    t, _ = gt
    result = t._compute_destination_path("/src/foo/a.txt")
    assert result == Path("/dst/foo/a.txt")


def test_compute_destination_path_outside_source_returns_none(gt):
    t, _ = gt
    result = t._compute_destination_path("/other/foo/a.txt")
    assert result is None
