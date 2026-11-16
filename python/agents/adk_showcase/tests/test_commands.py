"""The commands, as the tour lists and reads them."""

import re
from pathlib import Path

import pytest
import yaml

from src.commands import COMMANDS
from src.tour.menu import examples, menu_lines
from src.tour.routing import parse_input

SAMPLE_ROOT = Path(__file__).resolve().parents[1]
LISTED = [module.COMMAND for module in COMMANDS]


def test_every_command_lives_in_the_file_named_after_its_key():
    for module in COMMANDS:
        assert module.__name__ == f"src.commands.{module.COMMAND.key}"
        assert (SAMPLE_ROOT / module.COMMAND.source).is_file()


def test_keys_are_unique():
    keys = [command.key for command in LISTED]
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
    assert parse_input(text).key == expected


@pytest.mark.parametrize("text", ["", None, "   ", "tell me a joke", "show me"])
def test_unmatched_input_resolves_to_no_command(text):
    """Anything that is not a command falls through to the menu."""
    assert parse_input(text).key is None


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
    assert [command.key for command in LISTED if command.argument_hint] == ["llm"]
    assert next(command for command in LISTED if command.key == "llm").usage == "llm {prompt}"


def test_menu_lists_every_command_with_its_usage():
    rendered = "\n".join(menu_lines())
    for command in LISTED:
        assert f"  {command.usage} " in rendered


def test_examples_are_every_command_then_every_native_version():
    natives = [command for command in LISTED if command.native]
    assert len(examples()) == len(LISTED) + len(natives)
    for command, example in zip(LISTED, examples()):
        assert example.startswith(command.key)
    for command, example in zip(natives, examples()[len(LISTED):]):
        assert example.startswith(f"{command.key} native")


def test_the_footer_names_the_call_and_the_file():
    for command in LISTED:
        assert command.footer == f"\n\n↳ {command.api} · {command.source}"


def test_the_call_in_the_footer_is_written_in_the_command_file():
    """The SDK call a footer names is visible in the file the footer points at."""
    for command in LISTED:
        call = re.match(r"[\w.]+", command.api).group()
        source = (SAMPLE_ROOT / command.source).read_text(encoding="utf-8")
        assert call in source, f"{command.key}: `{call}` is missing from {command.source}"


def test_aion_yaml_advertises_the_examples_in_order():
    config = yaml.safe_load((SAMPLE_ROOT / "aion.yaml").read_text(encoding="utf-8"))
    (skill,) = config["aion"]["agents"]["showcase"]["skills"]
    assert skill["examples"] == examples()
