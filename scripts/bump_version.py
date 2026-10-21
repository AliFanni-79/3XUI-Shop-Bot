#!/usr/bin/env python3
"""Version bumping script for X-UI Shop Bot.

Supported version formats:
- Release:     YY.MAJOR.MINOR       (e.g., 26.2.2)
- Pre-release: YY.MAJOR.MINOR.PATCH (e.g., 26.2.2.1)

Modes:
- prerelease: Adds patch (.1) if missing, or increments existing patch.
              Year is updated to current 2-digit year.
- minor:      Bumps MINOR version, removes patch number.
              Year is updated to current 2-digit year.
- major:      Bumps MAJOR version, resets MINOR to 0, removes patch number.
              Year is updated to current 2-digit year.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
from pathlib import Path


def parse_version(raw: str) -> tuple[int, int, int, int | None]:
    """Parse version string into (year, major, minor, patch)."""
    clean = str(raw or "").strip().lstrip("vV")
    if not clean:
        raise ValueError("Empty version string")
    parts = clean.split(".")
    if len(parts) == 3:
        y, ma, mi = parts
        return int(y), int(ma), int(mi), None
    elif len(parts) >= 4:
        y, ma, mi, p = parts[:4]
        return int(y), int(ma), int(mi), int(p)
    else:
        raise ValueError(f"Version must have at least 3 parts (YY.MAJOR.MINOR), got: {raw}")


def compute_next_version(
    current: str,
    mode: str,
    override_year: int | None = None,
) -> str:
    """Calculate the next version string based on current version and mode."""
    curr_year = (
        override_year
        if override_year is not None
        else int(datetime.datetime.now(datetime.timezone.utc).strftime("%y"))
    )
    year, major, minor, patch = parse_version(current)

    if mode == "prerelease":
        new_year = curr_year
        new_major = major
        new_minor = minor
        if patch is None:
            new_patch = 1
        else:
            new_patch = patch + 1
        return f"{new_year}.{new_major}.{new_minor}.{new_patch}"

    elif mode == "minor":
        new_year = curr_year
        new_major = major
        new_minor = minor + 1
        return f"{new_year}.{new_major}.{new_minor}"

    elif mode == "major":
        new_year = curr_year
        if curr_year != year:
            new_major = 1
        else:
            new_major = major + 1
        new_minor = 0
        return f"{new_year}.{new_major}.{new_minor}"

    else:
        raise ValueError(f"Unknown bump mode: {mode}. Must be prerelease, minor, or major.")


def update_file_contents(file_path: Path, new_version: str) -> bool:
    """Update version in specified file if pattern matches."""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    name = file_path.name

    if name == "VERSION.txt":
        new_content = f"{new_version}\n"
    elif name == "__init__.py":
        new_content = re.sub(
            r'(VERSION\s*=\s*["\'])[^"\']+(["\'])',
            rf'\g<1>{new_version}\g<2>',
            content,
        )
    elif name == "package.json":
        new_content = re.sub(
            r'("version"\s*:\s*")[^"]+(")',
            rf'\g<1>{new_version}\g<2>',
            content,
        )
    else:
        return False

    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump version for X-UI Shop Bot.")
    parser.add_argument(
        "--mode",
        choices=["prerelease", "minor", "major"],
        required=True,
        help="Bump mode: prerelease, minor, or major",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Override current year (2-digit, e.g. 26)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print next version without writing files",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to repository root",
    )

    args = parser.parse_args()
    repo_root = args.repo_root

    version_file = repo_root / "VERSION.txt"
    if not version_file.exists():
        sys.stderr.write(f"Error: {version_file} does not exist\n")
        return 1

    current_ver = version_file.read_text(encoding="utf-8").strip()
    next_ver = compute_next_version(current_ver, args.mode, override_year=args.year)

    if args.dry_run:
        print(next_ver)
        return 0

    # Update files
    update_file_contents(version_file, next_ver)
    update_file_contents(repo_root / "xuishop" / "__init__.py", next_ver)
    update_file_contents(repo_root / "webapp" / "package.json", next_ver)

    # Output for GitHub Actions
    gh_output = os.getenv("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"version={next_ver}\n")
            f.write(f"tag=v{next_ver}\n")

    print(next_ver)
    return 0


if __name__ == "__main__":
    sys.exit(main())
