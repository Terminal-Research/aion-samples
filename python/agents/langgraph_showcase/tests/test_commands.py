"""Registry and parsing tests — no SDK or server required."""

import pytest

from src.commands import COMMANDS, examples, menu_lines, parse_command, parse_input


def test_keys_are_unique():
    """Each command has exactly one keyword, and no two share it."""
    keys = [command.key for command in COMMANDS]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("card", "card"),
        ("CARD", "card"),
        ("  card  ", "card"),
        ("/card", "card"),
        ("show me the card", "card"),
        ("data", "data"),
    ],
)
def test_input_resolves_to_command(text, expected):
    """Input is matched case-insensitively, past punctuation and filler words."""
    command = parse_command(text)
    assert command is not None
    assert command.key == expected


@pytest.mark.parametrize("text", ["", None, "   ", "tell me a joke", "show me"])
def test_unmatched_input_returns_none(text):
    """Anything that is not a command falls through to the menu."""
    assert parse_command(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("card What is A2A?", "What is A2A?"),
        ("card   Explain streaming, briefly.", "Explain streaming, briefly."),
        ("Show me the card What is A2A?", "What is A2A?"),
        ("card", ""),
    ],
)
def test_argument_is_taken_verbatim(text, expected):
    """Everything after the keyword reaches the command unchanged."""
    assert parse_input(text).argument == expected


def test_menu_spells_out_declared_arguments():
    """The menu spells out an argument exactly where one is accepted."""
    rendered = "\n".join(menu_lines())
    for command in COMMANDS:
        assert f"  {command.usage} " in rendered


def test_every_command_appears_in_menu_and_examples():
    """The menu and the agent card examples are generated from the registry."""
    rendered = "\n".join(menu_lines())
    for command in COMMANDS:
        assert command.key in rendered
    assert len(examples()) == len(COMMANDS)
    for command, example in zip(COMMANDS, examples()):
        assert example.startswith(command.key)


def test_footer_points_at_api_and_source():
    """Every command names the SDK call and the file that implements it."""
    for command in COMMANDS:
        footer = command.footer()
        assert command.api in footer
        assert command.source in footer
        assert command.source.startswith("src/")
