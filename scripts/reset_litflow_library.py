#!/usr/bin/env python
"""Safely reset LitFlow local library runtime data."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path


TABLES_TO_CLEAR = [
    "papertopic",
    "paperauthor",
    "paperasset",
    "paperchunk",
    "papertext",
    "extraction",
    "author",
    "paper",
]

RUNTIME_DIRS_TO_CLEAR = [
    "pdfs",
    "assets",
    "library",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def database_path(root: Path) -> Path:
    # Must stay aligned with backend/app/db/session.py:
    # DATABASE_PATH = PROJECT_ROOT / "storage" / "litflow.db"
    return root / "storage" / "litflow.db"


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_row_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
    return int(row[0]) if row else 0


def reset_database(db_path: Path, dry_run: bool) -> None:
    if not db_path.exists():
        print(f"Database skipped: {db_path} does not exist")
        return

    print(f"Database: {db_path}")
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        for table_name in TABLES_TO_CLEAR:
            if not table_exists(connection, table_name):
                print(f"  skipped table {table_name}: does not exist")
                continue

            count = table_row_count(connection, table_name)
            action = "would delete" if dry_run else "deleted"
            print(f"  {action} {count} rows from {table_name}")
            if not dry_run:
                connection.execute(f'DELETE FROM "{table_name}"')

        if not dry_run and table_exists(connection, "sqlite_sequence"):
            for table_name in TABLES_TO_CLEAR:
                connection.execute(
                    "DELETE FROM sqlite_sequence WHERE name = ?",
                    (table_name,),
                )

        if dry_run:
            connection.rollback()
        else:
            connection.commit()


def clear_directory_contents(directory: Path, dry_run: bool) -> tuple[int, int]:
    deleted_files = 0
    deleted_dirs = 0

    if not directory.exists():
        print(f"Directory skipped: {directory} does not exist")
        return deleted_files, deleted_dirs

    for child in directory.iterdir():
        if child.name == ".gitkeep":
            continue

        if child.is_dir():
            nested_files, nested_dirs = clear_directory_contents(child, dry_run)
            deleted_files += nested_files
            deleted_dirs += nested_dirs
            if not contains_gitkeep(child):
                print(f"  {'would remove' if dry_run else 'removed'} directory {child}")
                deleted_dirs += 1
                if not dry_run:
                    if any(child.iterdir()):
                        shutil.rmtree(child)
                    else:
                        child.rmdir()
        else:
            print(f"  {'would delete' if dry_run else 'deleted'} file {child}")
            deleted_files += 1
            if not dry_run:
                child.unlink()

    return deleted_files, deleted_dirs


def contains_gitkeep(directory: Path) -> bool:
    if not directory.exists():
        return False
    return any(path.name == ".gitkeep" for path in directory.rglob(".gitkeep"))


def reset_storage(root: Path, dry_run: bool) -> None:
    storage_dir = root / "storage"
    print(f"Storage: {storage_dir}")
    print(f"  preserved directory {storage_dir / 'rankings'}")

    for dirname in RUNTIME_DIRS_TO_CLEAR:
        target = storage_dir / dirname
        print(f"Clearing {target}")
        deleted_files, deleted_dirs = clear_directory_contents(target, dry_run)
        action = "would remove" if dry_run else "removed"
        print(f"  {action} {deleted_files} files and {deleted_dirs} directories under {target}")


def require_confirmation() -> None:
    print("This will delete LitFlow local library runtime data.")
    print("It will not delete code, .env files, README files, or storage/rankings.")
    confirmation = input("Type RESET to continue: ")
    if confirmation != "RESET":
        raise SystemExit("Aborted: confirmation did not match RESET.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset LitFlow local library runtime data safely.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting anything.",
    )
    args = parser.parse_args()

    root = project_root()
    print(f"Project root: {root}")
    print("Research topics are preserved; only paper-topic links are cleared.")

    if args.dry_run:
        print("Mode: dry-run")
    else:
        print("Mode: reset")
        require_confirmation()

    reset_database(database_path(root), args.dry_run)
    reset_storage(root, args.dry_run)

    if args.dry_run:
        print("Dry-run complete. No files or database rows were deleted.")
    else:
        print("Reset complete.")


if __name__ == "__main__":
    main()
