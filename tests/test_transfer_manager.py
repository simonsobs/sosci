from unittest.mock import MagicMock, patch

import pytest

from sosci.config import Config
from sosci.managers.transfer import BATCH_SIZE, TransferManager


@pytest.fixture
def manager(config_dict, logger):
    with patch("sosci.managers.transfer.GlobusTransfer") as MockGT:
        MockGT.return_value = MagicMock()
        cfg = Config(**config_dict)
        mgr = TransferManager(cfg, logger)
        yield mgr


def test_init_creates_one_client_per_destination(config_dict, logger):
    config_dict["destination"].append(dict(config_dict["destination"][0]))
    with patch("sosci.managers.transfer.GlobusTransfer") as MockGT:
        MockGT.return_value = MagicMock()
        mgr = TransferManager(Config(**config_dict), logger)
    assert len(mgr.transfer_clients) == 2


def test_to_transfer_accumulates(manager):
    manager.to_transfer(created=["a"], deleted=["d"], modified=["m"])
    manager.to_transfer(created=["b"], deleted=[], modified=[])
    assert manager._modified_files == ["a", "m", "b"]
    assert manager._deleted_files == ["d"]


def test_transfer_drains_and_calls_clients(manager):
    client = manager.transfer_clients[0]
    manager.to_transfer(created=["a"], deleted=["d"], modified=["m"])
    manager._transfer()

    client.transfer.assert_called_once_with(["a", "m"])
    client.delete.assert_called_once_with(["d"])
    assert manager._modified_files == []
    assert manager._deleted_files == []


def test_transfer_noop_when_empty(manager):
    manager._transfer()
    manager.transfer_clients[0].transfer.assert_not_called()
    manager.transfer_clients[0].delete.assert_not_called()


def test_transfer_batches_large_lists(manager):
    client = manager.transfer_clients[0]
    files = [f"f{i}" for i in range(BATCH_SIZE * 2 + 5)]
    manager.to_transfer(created=files, deleted=[], modified=[])
    manager._transfer()
    assert client.transfer.call_count == 3


def test_transfer_swallows_client_errors(manager):
    client = manager.transfer_clients[0]
    client.transfer.side_effect = RuntimeError("boom")
    manager.to_transfer(created=["a"], deleted=[], modified=[])
    manager._transfer()  # must not raise


def test_transfer_multi_destination(config_dict, logger):
    config_dict["destination"].append(dict(config_dict["destination"][0]))
    with patch("sosci.managers.transfer.GlobusTransfer") as MockGT:
        MockGT.side_effect = [MagicMock(), MagicMock()]
        mgr = TransferManager(Config(**config_dict), logger)
    mgr.to_transfer(created=["a"], deleted=["d"], modified=[])
    mgr._transfer()
    for c in mgr.transfer_clients:
        c.transfer.assert_called_once_with(["a"])
        c.delete.assert_called_once_with(["d"])


def test_start_stop_lifecycle(manager):
    manager.start()
    assert manager.running is True
    assert manager._worker.is_alive()
    manager.stop()
    assert manager.running is False
    assert not manager._worker.is_alive()


def test_stop_drains_pending_work(manager):
    client = manager.transfer_clients[0]
    manager.start()
    manager.to_transfer(created=["late"], deleted=[], modified=[])
    manager.stop()
    # Final drain in stop() should have shipped "late"
    assert any(call.args[0] == ["late"] for call in client.transfer.call_args_list)
