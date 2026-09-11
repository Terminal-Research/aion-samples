"""Registry and parsing tests — no SDK or server required."""

import re
from pathlib import Path

import pytest

from src.commands import COMMANDS, examples, menu_lines, parse_command, parse_input

SAMPLE_ROOT = Path(__file__).resolve().parents[1]


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
        ("llm What is the A2A protocol?", "llm"),
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
        ("llm What is A2A?", "What is A2A?"),
        ("llm   Explain streaming, briefly.", "Explain streaming, briefly."),
        ("Please llm What is A2A?", "What is A2A?"),
        ("LLM: what is a {prompt}?", "what is a {prompt}?"),
        ("llm", ""),
        ("card What is A2A?", "What is A2A?"),
    ],
)
def test_argument_is_taken_verbatim(text, expected):
    """Everything after the keyword reaches the command unchanged."""
    assert parse_input(text).argument == expected


def test_llm_is_the_command_that_takes_a_prompt():
    """`llm` is the one command with an argument, and the menu shows it."""
    llm = next(command for command in COMMANDS if command.key == "llm")
    assert llm.argument_hint == "prompt"
    assert llm.usage == "llm {prompt}"
    assert [command.key for command in COMMANDS if command.argument_hint] == ["llm"]


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


def test_the_call_in_the_footer_is_written_in_the_source_file():
    """The SDK call a footer names is visible in the file the footer points at.

    That is the promise the footer makes, and it is the reason handlers call the
    SDK themselves instead of going through a reply helper. Checking it here
    keeps a future helper from quietly hiding the call again.
    """
    for command in COMMANDS:
        call = re.match(r"[\w.]+", command.api).group()
        source = (SAMPLE_ROOT / command.source).read_text(encoding="utf-8")
        assert call in source, f"{command.key}: `{call}` is missing from {command.source}"
