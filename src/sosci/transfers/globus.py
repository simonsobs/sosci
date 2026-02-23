    
class GlobusTransfer:
    def __init__(self, source: str, destination: str, globus_config: Dict[str, str], logger: Logger):
        self.source = source
        self.destination = destination
        self.config = globus_config
        self.logger = logger
        
    def transfer(self) -> bool:
        final_source_path = (
            Path(args.source_path).relative_to(args.source_globus_root_path)
            if args.source_globus_root_path
            else Path(args.source_path)
        )
        logger.debug(f"final_source_path: {final_source_path}")
        destination_path = Path(args.destination_path)
        final_destin_path = (
            destination_path.relative_to(args.destination_globus_root_path)
            if args.destination_globus_root_path
            else destination_path
        )
        logger.debug(f"final_destin_path: {final_destin_path}")
        files_transferred = 1
        if not args.metadata_update_only:
            # Load Globus tokens
            tokens_adapter = SimpleJSONFileAdapter(
                os.path.expanduser(args.globus_refresh_token_file)
            )
            tokens = tokens_adapter.get_token_data("transfer.api.globus.org")

            # Setup Globus SDK client and authorizer
            client = globus_sdk.NativeAppAuthClient(client_id=args.globus_client_id)
            authorizer = globus_sdk.RefreshTokenAuthorizer(
                refresh_token=tokens["refresh_token"],
                auth_client=client,
                access_token=tokens["access_token"],
                expires_at=tokens["expires_at_seconds"],
            )
            transfer_client = globus_sdk.TransferClient(authorizer=authorizer)

            # Prepare and submit the transfer task
            task_data = globus_sdk.TransferData(
                source_endpoint=args.source_endpoint,
                destination_endpoint=args.destination_endpoint,
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
            logger.info("Metadata transfer task submitted")
            task_id = task_doc["task_id"]

            # Poll the transfer task status until it completes
            while task_doc.get("status", None) != "SUCCEEDED":
                task_doc = transfer_client.get_task(task_id)
                sleep(60)
            logger.info("metadata transfer task completed")
            files_transferred = task_doc["files_transferred"]
