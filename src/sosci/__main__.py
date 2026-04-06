import json
import signal
import threading
from argparse import ArgumentParser
from logging import basicConfig, getLogger

from sosci.config import Config
from sosci.watchers.watcher import Watcher


def main() -> None:

    parser = ArgumentParser(description="sosci: Sync One Source to One Destination using Globus")
    parser.add_argument("--config", "-c", type=str, help="Path to JSON configuration file)", required=True)
    logger = getLogger(name="sosci")
    basicConfig(filename='sosci.log', level="DEBUG")

    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config_data = json.load(f)
        session_config = Config(**config_data)

    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown_event.set())

    transfer_manager = TransferManager(session_config, logger)
    watcher = Watcher(path=session_config.source.path,
                      poll_interval=session_config.poll_interval,
                      on_cycle_done=transfer_manager.to_transfer,
                      logger=logger)

    watcher.load_snapshot()
    watcher.watch()
    transfer_manager.start()

    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        logger.info("Shutting down...")
        watcher.stop()
        transfer_manager.stop()
