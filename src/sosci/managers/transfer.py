import threading as mt

from sosci.transfers.globus import GlobusTransfer

BATCH_SIZE = 128

class TransferManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.running = False
        self._worker = None
        self.transfer_clients = []
        self.transfer_queue_lock = mt.Lock()
        self._modified_files = []
        self._deleted_files = []
        self._run_event = mt.Event()

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
            self._modified_files.extend(created)
            self._modified_files.extend(modified)
            self._deleted_files.extend(deleted)

    def _transfer(self):
        with self.transfer_queue_lock:
            modified_files = self._modified_files
            deleted_files = self._deleted_files
            self._modified_files = []
            self._deleted_files = []

        if not modified_files and not deleted_files:
            return

        for i in range(0, len(modified_files), BATCH_SIZE):
            batch = modified_files[i:i + BATCH_SIZE]
            for transfer_client in self.transfer_clients:
                transfer_client.transfer(batch)

        for i in range(0, len(deleted_files), BATCH_SIZE):
            batch = deleted_files[i:i + BATCH_SIZE]
            for transfer_client in self.transfer_clients:
                transfer_client.delete(batch)

    def _run(self):
        while self.running:
            self._transfer()
            if self.running:
                self._run_event.wait(timeout=60)
                self._run_event.clear()

    def start(self):
        self.running = True
        self._worker = mt.Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop(self):
        self.running = False
        self._run_event.set()
        if self._worker:
            self._worker.join()
        self._transfer()
