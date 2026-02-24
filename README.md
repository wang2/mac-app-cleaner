# 🧹 macOS App Cleaner

A Python script to find and clean up leftover data from uninstalled macOS applications — reclaim disk space without third-party tools.

## Features

- **Orphan Scanner** — Automatically detects `~/Library` folders that don't belong to any installed app
- **Batch Cleanup** — Select multiple items at once (`1,3,5` / `1-5` / `all`)
- **Deep Search** — Scans 10+ Library sub-paths (Application Support, Caches, Preferences, Containers, etc.)
- **Dry Run by Default** — Lists files without touching anything unless you explicitly opt in
- **Backup Mode** — Move files to a Desktop backup folder instead of permanent deletion
- **System Protection** — Built-in whitelist prevents accidental deletion of system files
- **Keychain Reminder** — Prompts you to manually check Keychain Access for related entries

## Requirements

- macOS
- Python 3 (pre-installed on macOS)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/wang2/mac-app-cleaner.git
cd mac-app-cleaner

# Scan for orphaned app data
python3 cleanup_app_data.py --scan

# Clean a specific app by name (dry run)
python3 cleanup_app_data.py "AppName"
```

## Usage

### Scan for Orphans

```bash
python3 cleanup_app_data.py --scan
```

Lists all `~/Library/Application Support` folders without a matching installed `.app`. You can then select items interactively:

```
Found 12 potential orphans in Application Support:
1. [503.49 MB] SomeOldApp
2. [127.45 MB] AnotherApp
...

Select items to clean:
  - Enter numbers separated by commas: 1,3,5
  - Enter a range: 1-5
  - Enter 'all' to select everything
  - Enter 'q' to quit
```

### Clean a Specific App

```bash
# Dry run (default) — only lists what would be deleted
python3 cleanup_app_data.py "AppName"

# Backup to Desktop
python3 cleanup_app_data.py "AppName" --backup --force

# Permanently delete
python3 cleanup_app_data.py "AppName" --force
```

### Batch Scan + Delete

```bash
# Scan → select → backup
python3 cleanup_app_data.py --scan --backup --force

# Scan → select → permanently delete
python3 cleanup_app_data.py --scan --force
```

## Scanned Paths

| Path | Content |
| :--- | :--- |
| `~/Library/Application Support` | App data, databases |
| `~/Library/Caches` | Cache files |
| `~/Library/Preferences` | `.plist` config files |
| `~/Library/Saved Application State` | Window state |
| `~/Library/Logs` | Log files |
| `~/Library/Containers` | Sandboxed app data |
| `~/Library/Group Containers` | Shared app group data |
| `~/Library/Cookies` | Cookies |
| `~/Library/LaunchAgents` | Auto-launch daemons |
| `~/Library/WebKit` | WebKit storage |

## Safety

- **Dry run** is the default — nothing is deleted unless you pass `--force`
- **System paths** (`/System`, `/Library`, `/usr`, etc.) are never touched
- **Whitelist** filters out common system folders (Apple, Adobe, Google, etc.)
- **Backup mode** moves files to `~/Desktop/<AppName>_Cleanup_Backup/` so you can restore them
- **Keychain items** are never modified programmatically — the script only reminds you to check manually

## License
MIT
