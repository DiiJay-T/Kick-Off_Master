from src.data.player_identity import clean_player_display_name, normalise_player_name


def test_removes_numeric_export_suffix_only():
    assert clean_player_display_name("Kylian Mbappé 123") == "Kylian Mbappé"


def test_preserves_single_digit_suffix():
    assert clean_player_display_name("Player 7") == "Player 7"


def test_collapses_whitespace():
    assert clean_player_display_name("  Lionel   Messi  ") == "Lionel Messi"


def test_normalises_accents_for_secondary_matching():
    assert normalise_player_name("Jürgen  Klopp") == "jurgen klopp"


def test_empty_identity_is_safe():
    assert clean_player_display_name(None) == ""
    assert normalise_player_name(None) == ""
