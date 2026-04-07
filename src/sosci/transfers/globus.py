import os
from logging import Logger
from pathlib import Path
from typing import Dict

import globus_sdk
from globus_sdk.token_storage.legacy import SimpleJSONFileAdapter


class GlobusTransfer:
    def __init__(self, source: Dict[str, str], destination: Dict[str, str], globus_config: Dict[str, str], logger: Logger):
        self.source = source
        self.destination = destination
        self.config = globus_config
        self.logger = logger

        self.client = globus_sdk.NativeAppAuthClient(client_id=self.config["client_id"])

    def _get_authorizer(self):
        tokens_adapter = SimpleJSONFileAdapter(
            os.path.expanduser(self.config["refresh_token_file"])
        )
        tokens = tokens_adapter.get_token_data("transfer.api.globus.org")
        return globus_sdk.RefreshTokenAuthorizer(
            refresh_token=tokens["refresh_token"],
            auth_client=self.client,
            access_token=tokens["access_token"],
            expires_at=tokens["expires_at_seconds"],
        )

    def transfer(self, filenames: list[str]) -> str:

        authorizer = self._get_authorizer()
        transfer_client = globus_sdk.TransferClient(authorizer=authorizer)

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
            destination_path = Path(self.destination["path"]) / Path(filename).relative_to(self.source["path"])
            final_destin_path = (
                destination_path.relative_to(self.destination["globus_root_path"])
                if self.destination["globus_root_path"]
                else destination_path
            )
            self.logger.debug(f"Transfer final_destin_path: {final_destin_path}")

           # Prepare and submit the transfer task
            task_data.add_item(
                str(final_source_path), str(final_destin_path), recursive=False
            )

        task_doc = transfer_client.submit_transfer(task_data)
        self.logger.info("Metadata transfer task submitted")
        task_id = task_doc["task_id"]
        return task_id

    def delete(self, filenames: list[str]) -> str:
        authorizer = self._get_authorizer()
        transfer_client = globus_sdk.TransferClient(authorizer=authorizer)
        ddata = globus_sdk.DeleteData(
            endpoint=self.destination["endpoint"],
            recursive=False,   # set True if deleting directories
            label="My delete task",
        )
        for filename in filenames:

            destination_path = Path(self.destination["path"]) / Path(filename).relative_to(self.source["path"])
            final_destin_path = (
                destination_path.relative_to(self.destination["globus_root_path"])
                if self.destination["globus_root_path"]
                else destination_path
            )
            self.logger.debug(f"Deletion final_destin_path: {final_destin_path}")
            ddata.add_item(str(final_destin_path))
        delete_task = transfer_client.submit_delete(ddata)
        self.logger.info("Delete task submitted")
        delete_task_id = delete_task["task_id"]
        return delete_task_id
