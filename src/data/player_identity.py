"""Stable player identity and display-name helpers."""

import re
import unicodedata


def clean_player_display_name(value: object) -> str:
    """Clean obvious export suffixes without changing source records or player IDs."""
    if value is None:
        return ""
    name = unicodedata.normalize("NFKC", str(value))
    name = re.sub(r"\s+\d{2,}$", "", name)
    return re.sub(r"\s+", " ", name).strip()


def normalise_player_name(value: object) -> str:
    """Return a conservative accent-insensitive key for secondary name matching."""
    name = clean_player_display_name(value)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(char for char in name if not unicodedata.combining(char))
    name = re.sub(r"[^a-zA-Z0-9 ]", " ", name).lower()
    return re.sub(r"\s+", " ", name).strip()
