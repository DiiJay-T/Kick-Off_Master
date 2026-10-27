"""Download the public Wyscout research dataset into data/raw/.

The script preserves downloaded archives and extracts them locally. It does not
commit, upload, or modify the original dataset files.
"""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path


SOURCES = {
    "matches.zip": "https://ndownloader.figshare.com/files/14464622",
    "events.zip": "https://ndownloader.figshare.com/files/14464685",
    "players.json": "https://ndownloader.figshare.com/files/15073721",
    "teams.json": "https://ndownloader.figshare.com/files/15073697",
}


def download_file(url: str, destination: Path) -> None:
    """Download one source file, skipping it if a non-empty copy exists."""
    if destination.exists() and destination.stat().st_size > 0:
        print(f"Already downloaded: {destination.name}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")

    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "KICK-OFF-football-research/1.0"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            with temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
        temporary.replace(destination)
        print(f"Downloaded: {destination.name}")
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def safe_extract(archive: Path, destination: Path) -> None:
    """Extract ZIP entries while preventing path traversal."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Unsafe path in archive: {member.filename}")
        zipped.extractall(destination)

    print(f"Extracted: {archive.name} -> {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the public Wyscout research dataset."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
        help="Local destination (default: data/raw).",
    )
    args = parser.parse_args()

    raw_dir = args.output_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in SOURCES.items():
        download_file(url, raw_dir / filename)

    safe_extract(raw_dir / "matches.zip", raw_dir / "matches")
    safe_extract(raw_dir / "events.zip", raw_dir / "events")

    print("\nWyscout download complete.")
    print(f"Raw data location: {raw_dir.resolve()}")
    print("Next: run the match validator against the extracted matches folder.")


if __name__ == "__main__":
    main()
