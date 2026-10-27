"""Read-only validation report for downloaded Wyscout match metadata."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


MATCH_REQUIRED_FIELDS = (
    "wyId",
    "dateutc",
    "competitionId",
    "seasonId",
    "teamsData",
)
TEAM_REQUIRED_FIELDS = ("teamId", "side", "score", "formation")
SUBSTITUTION_REQUIRED_FIELDS = ("minute", "playerIn", "playerOut")


def _read_matches(path: Path) -> list[dict[str, Any]]:
    """Read a Wyscout match file without changing it."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        matches = payload.get("matches")
    elif isinstance(payload, list):
        matches = payload
    else:
        raise ValueError("Top-level JSON must be a list or an object with 'matches'.")

    if not isinstance(matches, list):
        raise ValueError("Expected the 'matches' value to be a list.")

    return [match for match in matches if isinstance(match, dict)]


def _is_integer_like(value: Any) -> bool:
    try:
        int(value)
        return value is not None
    except (TypeError, ValueError):
        return False


def validate_match_files(directory: str | Path) -> dict[str, Any]:
    """Inspect matches_*.json files and return aggregate quality metrics.

    The function is read-only: it never edits, renames, or deletes source files.
    """
    root = Path(directory)
    files = sorted(root.glob("matches_*.json"))
    if not files:
        raise FileNotFoundError(f"No matches_*.json files found in {root}")

    report: dict[str, Any] = {
        "directory": str(root),
        "files_inspected": len(files),
        "file_reports": [],
        "total_matches": 0,
        "unique_match_ids": 0,
        "duplicate_match_ids": 0,
        "missing_match_fields": {},
        "teams_missing_required_fields": 0,
        "substitution_entries": 0,
        "valid_substitutions": 0,
        "malformed_substitutions": 0,
        "substitution_field_errors": {},
        "files_with_read_errors": [],
    }

    seen_ids: set[str] = set()
    duplicate_ids: Counter[str] = Counter()
    missing_match_fields: Counter[str] = Counter()
    substitution_field_errors: Counter[str] = Counter()

    for file_path in files:
        try:
            matches = _read_matches(file_path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            report["files_with_read_errors"].append(
                {"file": file_path.name, "error": str(error)}
            )
            continue

        file_valid_subs = 0
        file_malformed_subs = 0
        file_duplicate_ids = 0

        for match in matches:
            report["total_matches"] += 1

            for field in MATCH_REQUIRED_FIELDS:
                if match.get(field) is None:
                    missing_match_fields[field] += 1

            match_id = match.get("wyId")
            if match_id is not None:
                normalized_id = str(match_id)
                if normalized_id in seen_ids:
                    duplicate_ids[normalized_id] += 1
                    file_duplicate_ids += 1
                else:
                    seen_ids.add(normalized_id)

            teams_data = match.get("teamsData")
            if not isinstance(teams_data, dict):
                continue

            for team in teams_data.values():
                if not isinstance(team, dict):
                    report["teams_missing_required_fields"] += 1
                    continue

                if any(team.get(field) is None for field in TEAM_REQUIRED_FIELDS):
                    report["teams_missing_required_fields"] += 1

                formation = team.get("formation")
                if not isinstance(formation, dict):
                    continue

                substitutions = formation.get("substitutions")
                if substitutions is None:
                    continue
                if not isinstance(substitutions, list):
                    report["malformed_substitutions"] += 1
                    file_malformed_subs += 1
                    substitution_field_errors["substitutions_not_a_list"] += 1
                    continue

                for substitution in substitutions:
                    report["substitution_entries"] += 1
                    errors = []

                    if not isinstance(substitution, dict):
                        errors.append("entry_not_an_object")
                    else:
                        for field in SUBSTITUTION_REQUIRED_FIELDS:
                            if not _is_integer_like(substitution.get(field)):
                                errors.append(f"invalid_{field}")

                    if errors:
                        report["malformed_substitutions"] += 1
                        file_malformed_subs += 1
                        substitution_field_errors.update(errors)
                    else:
                        report["valid_substitutions"] += 1
                        file_valid_subs += 1

        report["file_reports"].append(
            {
                "file": file_path.name,
                "matches": len(matches),
                "valid_substitutions": file_valid_subs,
                "malformed_substitutions": file_malformed_subs,
                "duplicate_match_ids": file_duplicate_ids,
            }
        )

    report["unique_match_ids"] = len(seen_ids)
    report["duplicate_match_ids"] = sum(duplicate_ids.values())
    report["duplicate_ids"] = dict(duplicate_ids)
    report["missing_match_fields"] = dict(missing_match_fields)
    report["substitution_field_errors"] = dict(substitution_field_errors)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect Wyscout match JSON files without modifying raw data."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing matches_*.json files (default: data/raw).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for saving a JSON copy of the report.",
    )
    args = parser.parse_args()

    report = validate_match_files(args.data_dir)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
