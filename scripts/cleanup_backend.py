#!/usr/bin/env python3
"""
Clean up duplicate and archived backend files.
Run with --dry-run first to see what would be removed.

This script removes:
- Old archived backend directories
- Legacy Flask-based API files
- Archived test files from the migration
- Debug scripts that are no longer needed

Last run: 2025-12-14 - Removed 6 files/directories, freed 142KB
"""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Define cleanup targets - archived and duplicate files
    targets = [
        "backend-api-archive-20251211/",  # Old archive directory
        "backend-api/",  # Archived backend directory (now just README)
        "api/api_flask_archived.py",  # Old Flask-based API
        "api/debug_server.py",  # Archived debug script
        "api/test_keys.py",  # Archived test file
        "api/test_status.py",  # Archived test file
        # Add more based on analysis
    ]

    print("Backend Cleanup Script")
    print("=" * 50)

    if args.dry_run:
        print("DRY RUN MODE - No files will be deleted")
        print()

    removed_count = 0
    total_size = 0

    for target in targets:
        path = Path(target)
        if path.exists():
            # Calculate size for reporting
            if path.is_file():
                size = path.stat().st_size
            elif path.is_dir():
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            else:
                size = 0

            if args.dry_run:
                print(f"[DRY RUN] Would remove: {target} ({size} bytes)")
            else:
                try:
                    if path.is_dir():
                        import shutil

                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    print(f"✓ Removed: {target} ({size} bytes)")
                    removed_count += 1
                    total_size += size
                except Exception as e:
                    print(f"✗ Failed to remove {target}: {e}")
        else:
            print(f"⚠ Not found: {target}")

    print()
    print("Summary:")
    print(f"  Files/Directories processed: {len(targets)}")
    if not args.dry_run:
        print(f"  Successfully removed: {removed_count}")
        print(
            f"  Total space freed: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)"
        )

    if args.dry_run:
        print()
        print("Run without --dry-run to actually remove these files.")


if __name__ == "__main__":
    main()
