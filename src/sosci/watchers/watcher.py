import os
import pickle
import re
import time
from functools import partial
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers.api import BaseObserver
from watchdog.observers.polling import PollingEmitter
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

EXCLUDE_PATTERN = re.compile(r'_local\.')


def is_file_stable(path, checks=3, interval=2):
    """
    Check if a file has stopped growing by sampling its size
    multiple times. Returns True if size is stable.
    """
    try:
        prev_size = os.path.getsize(path)
        for _ in range(checks):
            time.sleep(interval)
            curr_size = os.path.getsize(path)
            if curr_size != prev_size:
                return False
            prev_size = curr_size
        return True
    except FileNotFoundError:
        return False


class _CallbackPollingEmitter(PollingEmitter):
    def __init__(self, event_queue, watch, *, timeout, callback, **kwargs):
        super().__init__(event_queue, watch, timeout=timeout, **kwargs)
        self._callback = callback

    def queue_events(self, timeout):
        super().queue_events(timeout)
        if self.should_keep_running():
            self._callback()


class Watcher(FileSystemEventHandler):

    def __init__(self, path, poll_interval=10, snapshot_path=None,
                 on_cycle_done=None, logger=None):
        self.path = path
        self.poll_interval = poll_interval
        self.snapshot_path = Path(snapshot_path) if snapshot_path else Path.home() / ".sosci" / "sosci_snapshot.pkl"
        self.logger = logger
        self.files_created = []
        self.files_deleted = []
        self.files_modified = []
        self._on_cycle_done = on_cycle_done

        emitter_class = partial(_CallbackPollingEmitter, callback=self._cycle_done)
        self.observer = BaseObserver(emitter_class, timeout=poll_interval)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)


    def _is_excluded(self, path):
        return EXCLUDE_PATTERN.search(os.path.basename(path)) is not None

    def _cycle_done(self):
        """Called by the emitter at the end of each polling cycle."""
        if not (self.files_created or self.files_deleted
                or self.files_modified):
            return

        if self._on_cycle_done:
            self._on_cycle_done(
                created=self.files_created[:],
                deleted=self.files_deleted[:],
                modified=self.files_modified[:],
            )

        self.files_created.clear()
        self.files_deleted.clear()
        self.files_modified.clear()

    def on_created(self, event):
        if event.is_directory or self._is_excluded(event.src_path):
            return
        path = event.src_path
        stable = is_file_stable(path, checks=5, interval=10)
        if stable:
            self.files_created.append(path)

    def on_deleted(self, event):
        if event.is_directory or self._is_excluded(event.src_path):
            return
        self.files_deleted.append(event.src_path)

    def on_modified(self, event):
        if event.is_directory or self._is_excluded(event.src_path):
            return
        self.files_modified.append(event.src_path)

    def load_snapshot(self):
        """Load a previous DirectorySnapshot and diff it against the current
        filesystem state. Populates the created/deleted/modified/moved lists
        with changes that occurred while the watcher was down.
        Returns the DirectorySnapshotDiff, or None if no snapshot exists."""
        if not os.path.exists(self.snapshot_path):
            return None

        with open(self.snapshot_path, "rb") as f:
            previous = pickle.load(f)

        current = DirectorySnapshot(self.path, recursive=True)
        diff = DirectorySnapshotDiff(previous, current)

        self.files_created.extend(diff.files_created)
        self.files_deleted.extend(diff.files_deleted)
        self.files_modified.extend(diff.files_modified)

        if self.logger:
            self.logger.info(
                f"Snapshot diff: {len(diff.files_created)} created, "
                f"{len(diff.files_deleted)} deleted, "
                f"{len(diff.files_modified)} modified, "
            )

        return diff

    def save_snapshot(self):
        """Take a DirectorySnapshot of the watched path and persist it."""
        snapshot = DirectorySnapshot(self.path, recursive=True)
        with open(self.snapshot_path, "wb") as f:
            pickle.dump(snapshot, f)

        if self.logger:
            self.logger.info(f"Snapshot saved to {self.snapshot_path}")

    def watch(self):
        self.observer.schedule(self, self.path, recursive=True)

        self.observer.start()
        if self.logger:
            self.logger.info(f"Watching '{self.path}' (polling every {self.poll_interval}s)")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.save_snapshot()
