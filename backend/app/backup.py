"""Create a consistent SQLite snapshot without replacing an existing file.

Run: python -m app.backup /path/to/bankguard.db /path/to/new-snapshot.db
Restore by validating the snapshot and pointing BANKGUARD_DATABASE_URL to a
separate copy while the API is stopped; never overwrite a running database.
"""

import argparse
import os
import sqlite3
from pathlib import Path


def snapshot_database(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination = destination.absolute()
    # SQLite's online backup includes committed WAL pages. A plain file copy
    # can lose them. Read-only URI also prevents creating a missing source.
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            with sqlite3.connect(destination) as backup:
                original.backup(backup)
                if backup.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise ValueError("Snapshot failed SQLite integrity validation")
        except BaseException:
            # This function created this destination exclusively; no user file
            # existed there. Only remove the incomplete snapshot on failure.
            destination.unlink(missing_ok=True)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    snapshot_database(args.source, args.destination)
    print(f"Verified snapshot created: {args.destination}")


if __name__ == "__main__":
    main()
