#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple

# Safety: Paths that should never be touched
SAFE_PATHS = [
    "/System",
    "/Library",
    "/bin",
    "/sbin",
    "/usr",
    "/etc",
    "/var",
    "/private/var",
    "/opt",
]

# User Library Paths to scan
USER_LIBRARY_PATHS = [
    "~/Library/Application Support",
    "~/Library/Caches",
    "~/Library/Preferences",
    "~/Library/Saved Application State",
    "~/Library/Logs",
    "~/Library/Containers",
    "~/Library/Group Containers",
    "~/Library/Cookies",
    "~/Library/LaunchAgents",
    "~/Library/WebKit",
]

def expanded_path(path_str: str) -> Path:
    return Path(path_str).expanduser().resolve()

def is_safe_path(path: Path) -> bool:
    """Check if the path is safe to delete (not a system path)."""
    resolved_path = path.resolve()
    for safe in SAFE_PATHS:
        if str(resolved_path).startswith(safe):
            return False
    # Ensure we are in the user's home directory
    if not str(resolved_path).startswith(str(Path.home())):
        return False
    return True

def find_app_paths(app_name: str) -> List[Path]:
    """Finds paths containing the app name in standard library locations."""
    found_paths = []
    # Normalize app name for searching
    search_term = app_name.lower()
    
    for lib_path_str in USER_LIBRARY_PATHS:
        lib_path = expanded_path(lib_path_str)
        if not lib_path.exists():
            continue
            
        try:
            for item in lib_path.iterdir():
                if search_term in item.name.lower():
                    found_paths.append(item)
        except PermissionError:
            print(f"Permission denied: {lib_path}")
            
    return found_paths

def find_keychain_items(app_name: str) -> List[str]:
    """Finds keychain items related to the app."""
    try:
        # security dump-keychain is restricted, but we can try 'find-generic-password' or similar
        # A broader search often requires admin privileges or specific queries.
        # For this script, we'll try a generic search which might prompt the user, 
        # so we will use a safer approach: listing non-sensitive attributes if possible, 
        # or just warning the user.
        # Actually, 'security find-generic-password -l "App Name"' is specific. 
        # listing *all* items matching a substring is harder without dumping.
        # We will use a grep approach on the dump output IF the user runs with sudo, 
        # otherwise we might just remind them. 
        # For now, let's stick to a simple reminder as programmatic keychain access is tricky/secure.
        return [] 
    except Exception:
        return []

def get_dir_size(path: Path) -> int:
    """Calculates total size of a directory."""
    total = 0
    if path.is_file():
        try:
            return path.stat().st_size
        except:
            return 0
    try:
        for p in path.rglob('*'):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except:
                    pass
    except:
        pass
    return total

def format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def check_app_installed(app_name: str) -> bool:
    """Checks if the app might still be installed."""
    search_dirs = ["/Applications", str(Path.home() / "Applications")]
    found = False
    for d in search_dirs:
        p = Path(d)
        if p.exists():
            for item in p.iterdir():
                if app_name.lower() in item.name.lower() and item.suffix == ".app":
                    print(f"WARNING: Found installed app possibly matching '{app_name}': {item}")
                    found = True
    return found

# Common shared folders to ignore during scan
SCAN_WHITELIST = [
    "Adobe", "Google", "Microsoft", "Mozilla", "Apple", "com.apple", 
    "Zoom", "Steam", "Discord", "Slack", "Telegram", "Logi", "Logitech",
    "Chromium", "Electron", "Sentry", "CrashReporter", "cef", "CEF",
    # System / Apple internal that might be in Application Support
    "AddressBook", "CloudDocs", "CallHistory", "CONTACTS", "FaceTime", 
    "FileProvider", "iCloud", "Knowledge", "SyncServices", "accountsd",
    "identityservicesd", "messages", "siri", "useractivityd", "ControlCenter",
    "CallHistoryTransactions", "CallHistoryDB", "locationaccessstored", 
    "homeenergyd", "appplaceholdersyncd", "tipsd", "privatecloudcomputed",
    "FamilySettings", "contactsd", "DifferentialPrivacy", "AskPermission",
    "Dock", "Animoji", "ConfigurationProfiles", "icdd"
]

def scan_for_orphans() -> List[Tuple[Path, int]]:
    """Scans Application Support for folders without matching installed apps."""
    orphans = []
    app_support = expanded_path("~/Library/Application Support")
    
    if not app_support.exists():
        return []
        
    print("Scanning for potential orphans...")
    
    # Cache installed apps to avoid repeated disk access
    installed_apps = set()
    for d in ["/Applications", str(Path.home() / "Applications")]:
        p = Path(d)
        if p.exists():
            for item in p.iterdir():
                if item.suffix == ".app":
                    installed_apps.add(item.stem.lower())

    for item in app_support.iterdir():
        if not item.is_dir():
            continue
            
        name = item.name
        # Skip whitelisted or system-like names
        if name in SCAN_WHITELIST or name.startswith("com.apple."):
            continue
            
        # Check if matched in installed apps (exact or substring match)
        # Heuristic: If 'name' is NOT found in any installed app name
        is_installed = False
        name_lower = name.lower()
        
        # Direct check
        if name_lower in installed_apps:
            is_installed = True
        else:
            # Substring check (e.g. 'ZoomInst' vs 'Zoom.app')
            for app in installed_apps:
                if name_lower in app or app in name_lower:
                    is_installed = True
                    break
        
        if not is_installed:
            size = get_dir_size(item)
            orphans.append((item, size))
            
    return sorted(orphans, key=lambda x: x[1], reverse=True)

def main():
    parser = argparse.ArgumentParser(description="Clean up data for uninstalled macOS apps.")
    parser.add_argument("app_name", nargs="?", help="Name of the application to clean up (optional if using --scan)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="List files without deleting (default)")
    parser.add_argument("--force", action="store_true", help="Actually delete files")
    parser.add_argument("--backup", action="store_true", help="Move to backup folder instead of deleting")
    parser.add_argument("--scan", action="store_true", help="Scan for potential orphan data")
    
    args = parser.parse_args()

    if args.scan:
        orphans = scan_for_orphans()
        if not orphans:
            print("No obvious orphans found.")
            return
            
        print(f"\nFound {len(orphans)} potential orphans in Application Support:")
        total_orphan_size = 0
        for idx, (path, size) in enumerate(orphans):
            total_orphan_size += size
            print(f"{idx + 1}. [{format_size(size)}] {path.name}")
        print(f"\nTotal Size: {format_size(total_orphan_size)}")
            
        print("\nSelect items to clean:")
        print("  - Enter numbers separated by commas: 1,3,5")
        print("  - Enter a range: 1-5")
        print("  - Enter 'all' to select everything")
        print("  - Enter 'q' to quit")
        choice = input("\nYour selection: ").strip()
        if choice.lower() == 'q':
            return

        # Parse selection
        selected_indices = _parse_selection(choice, len(orphans))
        if not selected_indices:
            print("No valid items selected.")
            return

        selected_orphans = [orphans[i] for i in selected_indices]
        selected_names = [o[0].name for o in selected_orphans]
        selected_total = sum(o[1] for o in selected_orphans)

        print(f"\nSelected {len(selected_orphans)} items ({format_size(selected_total)}):")
        for path, size in selected_orphans:
            print(f"  [{format_size(size)}] {path.name}")

        # Collect ALL matching paths across Library for the selected apps
        all_matches: List[Path] = []
        for app_name in selected_names:
            matches = find_app_paths(app_name)
            all_matches.extend(matches)

        if not all_matches:
            print("No matching files found in Library paths.")
            return

        print(f"\nFound {len(all_matches)} total items across all Library paths:")
        grand_total = 0
        for m in all_matches:
            size = get_dir_size(m)
            grand_total += size
            print(f"  [{format_size(size)}] {m}")
        print(f"\nTotal Size: {format_size(grand_total)}")

        # Keychain reminder
        print("\n[Keychain Check]")
        print(f"Please manually check Keychain Access.app for entries related to: {', '.join(selected_names)}")
        print("Script does not modify Keychain for security reasons.")

        # Action: dry-run, backup or delete
        if not args.force:
            print("\n--- DRY RUN ---")
            print("To delete these files, run with: --scan --force")
            print("To backup these files, run with: --scan --backup --force")
            return

        _execute_cleanup(all_matches, selected_names, args.backup)
        return

    # --- Single app mode ---
    if not args.app_name:
        parser.print_help()
        return
    app_name = args.app_name.strip()

    if len(app_name) < 3:
        print("Error: App name is too short. Please provide at least 3 characters to avoid false positives.")
        return

    print(f"Searching for data related to '{app_name}'...")
    
    matches = find_app_paths(app_name)
    
    if not matches:
        print(f"No data found for '{app_name}'.")
        return

    check_app_installed(app_name)
    
    print(f"\nFound {len(matches)} items:")
    total_size = 0
    for m in matches:
        size = get_dir_size(m)
        total_size += size
        print(f"[{format_size(size)}] {m}")
        
    print(f"\nTotal Size: {format_size(total_size)}")
    
    # Keychain reminder
    print("\n[Keychain Check]")
    print(f"Please manually check Keychain Access.app for entries named '{app_name}'.")
    print("Script does not modify Keychain for security reasons.")

    if args.dry_run and not args.force:
        print("\n--- DRY RUN ---")
        print("To delete these files, run with --force")
        print("To backup these files, run with --backup --force")
        return

    _execute_cleanup(matches, [app_name], args.backup)


def _parse_selection(choice: str, max_count: int) -> List[int]:
    """Parse user selection string into a sorted list of 0-based indices.
    
    Supports: 'all', single numbers '3', comma-separated '1,3,5',
    ranges '1-5', and combinations '1,3-5,8'.
    """
    if choice.lower() == 'all':
        return list(range(max_count))

    indices = set()
    parts = choice.replace(' ', '').split(',')
    for part in parts:
        if '-' in part:
            try:
                start, end = part.split('-', 1)
                start, end = int(start), int(end)
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    if 1 <= i <= max_count:
                        indices.add(i - 1)
            except ValueError:
                print(f"Warning: Ignoring invalid range '{part}'")
        else:
            try:
                num = int(part)
                if 1 <= num <= max_count:
                    indices.add(num - 1)
                else:
                    print(f"Warning: {num} is out of range (1-{max_count}), skipping.")
            except ValueError:
                print(f"Warning: Ignoring invalid input '{part}'")

    return sorted(indices)


def _execute_cleanup(matches: List[Path], app_names: List[str], backup: bool):
    """Execute backup or deletion for a list of matched paths."""
    if backup:
        label = "_".join(app_names) if len(app_names) <= 3 else f"{len(app_names)}_apps"
        backup_dir = Path.home() / "Desktop" / f"{label}_Cleanup_Backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nMoving files to {backup_dir}...")
        for item in matches:
            if not is_safe_path(item):
                print(f"Skipping unsafe path: {item}")
                continue
                
            dest = backup_dir / item.name
            counter = 1
            while dest.exists():
                stem = item.stem
                if item.suffix:
                    new_name = f"{stem}_{counter}{item.suffix}"
                else:
                    new_name = f"{stem}_{counter}"
                dest = backup_dir / new_name
                counter += 1

            try:
                shutil.move(str(item), str(dest))
                print(f"Moved: {item.name} -> {dest.name}")
            except Exception as e:
                print(f"Error moving {item}: {e}")
        print("Backup complete.")
        return

    # Force delete
    confirm = input(f"\nAre you sure you want to PERMANENTLY DELETE these {len(matches)} items? (yes/no): ")
    if confirm.lower() != "yes":
        print("Operation cancelled.")
        return

    print("\nDeleting files...")
    for item in matches:
        if not is_safe_path(item):
            print(f"Skipping unsafe path: {item}")
            continue
            
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            print(f"Deleted: {item}")
        except Exception as e:
            print(f"Error deleting {item}: {e}")
    print("\nCleanup complete.")

if __name__ == "__main__":
    main()
