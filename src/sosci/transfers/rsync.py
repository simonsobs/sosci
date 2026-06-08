import subprocess
from logging import Logger


class RsyncTransfer:

    def __init__(self, source: str, destination: str, logger: Logger):
        self.source = source
        self.destination = destination
        self.logger = logger

    def transfer(self, dry_run: bool = False) -> bool:
        cmd = ["rsync", "-avz", "--exclude=*_local*", "--exclude=.*"]

        if dry_run:
            cmd.append("--dry-run")

        # Ensure trailing slash on source to sync contents
        source = self.source.rstrip("/") + "/"
        cmd.extend([source, self.destination])

        self.logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self.logger.error(f"rsync failed: {result.stderr}")
            return False

        self.logger.info(result.stdout)
        self.logger.info("rsync transfer completed")
        return True
