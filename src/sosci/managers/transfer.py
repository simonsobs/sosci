import threading as mt

from sosci.transfers.globus import GlobusTransfer


class TransferManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.running = False
        self.transfer_clients = []
        self.transfer_queue_lock = mt.Lock()

        for dest in self.config.destination:
            transfer_client = GlobusTransfer(
                source={
                    "path": self.config.source.path,
                    "endpoint": self.config.source.endpoint,
                    "globus_root_path": self.config.source.globus_root_path,
                },
                destination={
                    "path": dest.path,
                    "endpoint": dest.endpoint,
                    "globus_root_path": dest.globus_root_path,
                },
                globus_config={
                    "client_id": dest.client_id,
                    "refresh_token_file": dest.refresh_token_file,
                },
                logger=self.logger,
            )
            self.transfer_clients.append(transfer_client)

    def to_transfer(self, created, deleted, modified):
        with self.transfer_queue_lock:
            self._modified_files = created + modified
            self._deleted_files = deleted
            for transfer_client in self.transfer_clients:
                transfer_client.transfer(self._modified_files)
            for transfer_client in self.transfer_clients:
                transfer_client.transfer(self._deleted_files)
    def start(self):
        self.running = True
        while self.running:
            if self.transfer_queue:
                transfer = self.transfer_queue.pop(0)
                try:
                    transfer.transfer()
                except Exception as e:
                    self.logger.error(f"Error during transfer: {e}")
            else:
                sleep(self.config.poll_interval)

    def stop(self):
        self.running = False
