# sosci

**S**imons **O**bservatory **S**oftware and **C**omputing **I**nfrastructure — a daemon that watches a local directory for file changes and automatically syncs them to one or more remote destinations using Globus.

## Features

- **Polling-based file watcher** — monitors a source directory for created, modified, and deleted files using watchdog's polling observer, compatible with any filesystem (including network mounts).
- **File stability detection** — waits for files to stop growing before triggering a transfer, avoiding partial uploads.
- **Multi-destination sync** — supports syncing to multiple Globus endpoints, each with its own authentication credentials.
- **Crash recovery via snapshots** — saves a `DirectorySnapshot` on shutdown. On restart, diffs the snapshot against the current filesystem to detect changes that occurred while the daemon was down.
- **Globus transfers** — uses the Globus SDK for reliable, encrypted, checksum-verified file transfers with automatic retry.
- **Rsync backend** — an alternative rsync-based transfer for local or SSH-accessible destinations.
- **Clean shutdown** — handles SIGTERM and SIGINT (Ctrl+C) to ensure all threads stop gracefully and snapshots are saved.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Main Thread                        │
│  - Parses config                                     │
│  - Wires watcher → transfer manager                  │
│  - Blocks until SIGTERM / SIGINT                     │
│  - Orchestrates clean shutdown                       │
└──────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────┐   ┌─────────────────────────┐
│   Watcher Thread     │   │  Transfer Manager Thread │
│  (PollingObserver)   │   │                          │
│                      │   │  - Receives file lists   │
│  - Polls source dir  │──▶│    via callback          │
│  - Detects changes   │   │  - Transfers to each     │
│  - Checks stability  │   │    Globus destination    │
│  - Calls on_cycle_   │   │  - Handles deletes       │
│    done callback     │   │                          │
└─────────────────────┘   └─────────────────────────┘
```

**Data flow:** Source directory → Watcher detects stable files → `on_cycle_done` callback → TransferManager syncs to all configured Globus destinations.

## Configuration

sosci is configured via a JSON file:

```json
{
  "source": {
    "path": "/data/experiment",
    "endpoint": "source-endpoint-uuid",
    "globus_root_path": "/root/path/on/source",
    "base_path": "/data/experiment"
  },
  "destination": [
    {
      "path": "/data/backup",
      "endpoint": "dest-endpoint-uuid",
      "globus_root_path": "/root/path/on/dest",
      "client_id": "globus-native-app-client-id",
      "refresh_token_file": "~/.globus/tokens.json"
    }
  ],
  "poll_interval": 30,
  "check_interval": 60,
  "max_retries": 3,
  "snapshot_path": "~/.sosci/sosci_snapshot.pkl"
}
```

| Field | Description |
|-------|-------------|
| `source` | Source directory and Globus endpoint configuration |
| `destination` | List of destination configurations, each with its own Globus credentials |
| `poll_interval` | Seconds between filesystem polls (default: 30) |
| `check_interval` | Seconds between modified-file checks during transfer (default: 60) |
| `max_retries` | Max checks for modified files before giving up (default: 3) |
| `snapshot_path` | Where to persist the directory snapshot for crash recovery (default: `~/.sosci/sosci_snapshot.pkl`) |

## Testing

Run the test suite with:

```bash
uv run pytest
```

## Usage

```bash
sosci --config config.json
```

Stop with Ctrl+C or `kill <pid>` — the daemon will save a snapshot and shut down cleanly.

[!NOTE]
README was edited with Claude AI.
