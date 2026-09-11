"""Dispatch tests — these import the Aion SDK and Google ADK."""

import inspect

from src.agent import HANDLERS, _inbound_text, create_agent
from src.commands import COMMANDS, parse_command


def test_every_command_has_a_handler():
    """The registry and the handler table stay in step."""
    assert set(HANDLERS) == {command.key for command in COMMANDS}


def test_every_handler_takes_the_context_and_an_argument():
    """One arity for all of them, so dispatch never branches on the command.

    The second parameter is the text typed after the keyword; handlers that
    accept none still take it and ignore it.
    """
    for key, handler in HANDLERS.items():
        parameters = list(inspect.signature(handler).parameters)
        assert len(parameters) == 2, f"{key}: {parameters}"
        assert parameters[0] == "ctx", f"{key}: {parameters}"


def test_agent_is_named_after_its_aion_yaml_entry():
    """The agent id in aion.yaml and the agent name match."""
    assert create_agent().name == "showcase"


def test_every_keyword_resolves_to_a_handler():
    """Anything the menu advertises can actually be dispatched."""
    for command in COMMANDS:
        resolved = parse_command(command.key)
        assert resolved is not None
        assert resolved.key in HANDLERS


def test_inbound_text_is_empty_without_a_runtime_context():
    """A turn with no Aion context falls through to the menu."""

    class _Ctx:
        aion_runtime_context = None

    assert _inbound_text(_Ctx()) == ""
