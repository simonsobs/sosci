from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    path: str = Field(..., description="Source path to sync from")
    endpoint: str = Field(..., description="Globus source endpoint UUID")
    globus_root_path: str = Field(..., description="Globus root path on the source endpoint")
    base_path: str = Field(..., description="Base path for the source, used for relative path calculations")


class DestinationConfig(BaseModel):
    path: str = Field(..., description="Destination path to sync to")
    endpoint: str = Field(..., description="Globus destination endpoint UUID")
    globus_root_path: str = Field(..., description="Globus root path on the destination endpoint")
    # Globus auth — per-destination credentials
    client_id: str = Field(..., description="Globus Native App client ID")
    refresh_token_file: str = Field(..., description="Path to Globus refresh token JSON file")


class Config(BaseModel):
    source: SourceConfig = Field(..., description="Source configuration")
    destination: list[DestinationConfig] = Field(..., description="Destination configuration")
    poll_interval: int = Field(30, description="Interval in seconds to poll for transfer status updates")
    check_interval: int = Field(60, description="Interval in seconds to check if files were modified during transfer")
    max_retries: int = Field(3, description="Maximum number of checks for modified files before giving up")
    snapshot_path: str = Field("~/.sosci/sosci_snapshot.pkl", description="Path to store the snapshot of the source directory")
