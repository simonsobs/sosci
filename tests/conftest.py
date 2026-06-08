import logging

import pytest


@pytest.fixture
def logger():
    return logging.getLogger("test")


@pytest.fixture
def config_dict(tmp_path):
    """Minimal valid Config dict, paths rooted in tmp_path."""
    src = tmp_path / "src"
    src.mkdir()
    return {
        "source": {
            "path": str(src),
            "endpoint": "src-uuid",
            "globus_root_path": str(tmp_path),
            "base_path": str(src),
        },
        "destination": [
            {
                "path": "/dst",
                "endpoint": "dst-uuid",
                "globus_root_path": "/",
                "client_id": "client-123",
                "refresh_token_file": str(tmp_path / "tokens.json"),
            }
        ],
        "poll_interval": 1,
        "snapshot_path": str(tmp_path / "snap.pkl"),
    }
