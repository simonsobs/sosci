import os
from pathlib import Path
from time import sleep
from logging import Logger
from typing import Dict

import globus_sdk
from globus_sdk.token_storage.legacy import SimpleJSONFileAdapter


class GlobusTransfer:
    def __init__(self, source: Dict[str, str], destination: Dict[str, str], globus_config: Dict[str, str], logger: Logger):
        self.source = source
        self.destination = destination
        self.config = globus_config
        self.logger = logger
        
    def transfer(self) -> bool:
        final_source_path = (
            Path(self.source["path"]).relative_to(self.source["globus_root_path"])
            if self.source["globus_root_path"]
            else Path(self.source["path"])
        )
        self.logger.debug(f"final_source_path: {final_source_path}")
        destination_path = Path(self.destination["path"])
        final_destin_path = (
            destination_path.relative_to(self.destination["globus_root_path"])
            if self.destination["globus_root_path"]
            else destination_path
        )
        self.logger.debug(f"final_destin_path: {final_destin_path}")
        # Load Globus tokens
        tokens_adapter = SimpleJSONFileAdapter(
            os.path.expanduser(self.config["refresh_token_file"])
        )
        tokens = tokens_adapter.get_token_data("transfer.api.globus.org")

        # Setup Globus SDK client and authorizer
        client = globus_sdk.NativeAppAuthClient(client_id=self.config["client_id"])
        authorizer = globus_sdk.RefreshTokenAuthorizer(
            refresh_token=tokens["refresh_token"],
            auth_client=client,
            access_token=tokens["access_token"],
            expires_at=tokens["expires_at_seconds"],
        )
        transfer_client = globus_sdk.TransferClient(authorizer=authorizer)

        # Prepare and submit the transfer task
        task_data = globus_sdk.TransferData(
            source_endpoint=self.source["endpoint"],
            destination_endpoint=self.destination["endpoint"],
            sync_level="mtime",
            verify_checksum=True,
            skip_source_errors=True,
            preserve_timestamp=True,
            fail_on_quota_errors=True,
            label="Metadata Sync from NERSC to PU",
            encrypt_data=True,
        )

        task_data.add_filter_rule("*_local*", method="exclude", type="file")
        task_data.add_filter_rule(".*", method="exclude")

        task_data.add_item(
            str(final_source_path), str(final_destin_path), recursive=True
        )

        task_doc = transfer_client.submit_transfer(task_data)
        self.logger.info("Metadata transfer task submitted")
        task_id = task_doc["task_id"]

        # Poll the transfer task status until it completes
        while task_doc.get("status", None) != "SUCCEEDED":
            task_doc = transfer_client.get_task(task_id)
            sleep(60)
        self.logger.info("metadata transfer task completed")
        files_transferred = task_doc["files_transferred"]

        return files_transferred > 0