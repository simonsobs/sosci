import os
from logging import Logger
from pathlib import Path
from time import sleep
from typing import Dict

import globus_sdk
from globus_sdk.token_storage.legacy import SimpleJSONFileAdapter


class GlobusTransfer:
    def __init__(self, source: Dict[str, str], destination: Dict[str, str], globus_config: Dict[str, str], logger: Logger):
        self.source = source
        self.destination = destination
        self.config = globus_config
        self.logger = logger
        tokens_adapter = SimpleJSONFileAdapter(
            os.path.expanduser(self.config["refresh_token_file"])
        )

        tokens = tokens_adapter.get_token_data("transfer.api.globus.org")

        # Setup Globus SDK client and authorizer
        client = globus_sdk.NativeAppAuthClient(client_id=self.config["client_id"])
        self.authorizer = globus_sdk.RefreshTokenAuthorizer(
            refresh_token=tokens["refresh_token"],
            auth_client=client,
            access_token=tokens["access_token"],
            expires_at=tokens["expires_at_seconds"],
        )
        self.transfer_client = globus_sdk.TransferClient(authorizer=self.authorizer)


    def transfer(self, filenames: list[str]) -> bool:
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
        for filename in filenames:
            final_source_path = (
                Path(filename).relative_to(self.source["globus_root_path"])
                if self.source["globus_root_path"]
                else Path(filename)
            )
            self.logger.debug(f"final_source_path: {final_source_path}")
            destination_path = Path(filename) #TODO: this is the source path. It needs to change to the desitnation
            final_destin_path = (
                destination_path.relative_to(self.destination["globus_root_path"])
                if self.destination["globus_root_path"]
                else destination_path
            )
            self.logger.debug(f"final_destin_path: {final_destin_path}")
            # Load Globus tokens

        # Prepare and submit the transfer task


            task_data.add_item(
                str(final_source_path), str(final_destin_path), recursive=False
            )

        task_doc = self.transfer_client.submit_transfer(task_data)
        self.logger.info("Metadata transfer task submitted")
        task_id = task_doc["task_id"]

        # Poll the transfer task status until it completes
        while task_doc.get("status", None) != "SUCCEEDED":
            task_doc = self.transfer_client.get_task(task_id)
            sleep(60)
        self.logger.info("metadata transfer task completed")
        files_transferred = task_doc["files_transferred"]

        return files_transferred > 0

    def delete(self, filenames: list[str]) -> bool:
        # Globus does not support remote deletion, so we log a warning and return False
        self.logger.warning("Globus does not support remote deletion. Skipping delete operation.")
        ddata = globus_sdk.DeleteData(
            transfer_client=self.transfer_client,
            endpoint=self.destination["endpoint"],
            recursive=False,   # set True if deleting directories
            label="My delete task",
        )
        for filename in filenames:
            destination_path = Path(filename) #TODO: this is the source path. It needs to change to the desitnation
            final_destin_path = (
                destination_path.relative_to(self.destination["globus_root_path"])
                if self.destination["globus_root_path"]
                else destination_path
            )
            self.logger.debug(f"final_destin_path: {final_destin_path}")
            ddata.add_item(str(final_destin_path))
        delete_task = self.transfer_client.submit_delete(ddata)
        self.logger.info("Delete task submitted")
        delete_task_id = delete_task["task_id"]
