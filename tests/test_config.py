import pytest
from pydantic import ValidationError

from sosci.config import Config, DestinationConfig, SourceConfig


def test_config_minimal(config_dict):
    cfg = Config(**config_dict)
    assert isinstance(cfg.source, SourceConfig)
    assert len(cfg.destination) == 1
    assert isinstance(cfg.destination[0], DestinationConfig)
    assert cfg.poll_interval == 1


def test_config_defaults(config_dict):
    config_dict.pop("poll_interval")
    config_dict.pop("snapshot_path")
    cfg = Config(**config_dict)
    assert cfg.poll_interval == 30
    assert cfg.check_interval == 60
    assert cfg.max_retries == 3
    assert cfg.snapshot_path == "~/.sosci/sosci_snapshot.pkl"


def test_config_multiple_destinations(config_dict):
    config_dict["destination"].append(dict(config_dict["destination"][0]))
    cfg = Config(**config_dict)
    assert len(cfg.destination) == 2


def test_config_missing_source(config_dict):
    config_dict.pop("source")
    with pytest.raises(ValidationError):
        Config(**config_dict)


def test_config_missing_destination_field(config_dict):
    config_dict["destination"][0].pop("client_id")
    with pytest.raises(ValidationError):
        Config(**config_dict)
