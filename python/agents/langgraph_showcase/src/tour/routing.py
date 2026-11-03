"""Which node answers a turn: read the keyword and ``native``, then pick the node."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src import commands
from src.tour.state import TourState

NATIVE = "native"
"""The word after a keyword that asks for LangGraph's own way."""

_FILLER_WORDS = frozenset({"show", "demo", "run", "do", "me", "the", "a", "an", "please"})
_PUNCTUATION = re.compile(r"[^\w\s-]")


@dataclass(frozen=True)
class ParsedInput:
    """The command a text names, whether ``native`` follows it, and the text after them."""

    key: str | None
    argument: str
    native: bool = False


def parse_input(text: str | None) -> ParsedInput:
    """Read a command, the ``native`` flag and the argument from free-form text.

    The first meaningful word selects the command, so ``card``, ``Show me the
    card`` and ``/card`` all select it; ``native`` right after it asks for
    LangGraph's own way; the rest is the argument, kept verbatim.
    """
    words = (text or "").split()
    index = 0
    while index < len(words) and _normalize(words[index]) in _FILLER_WORDS:
        index += 1
    key = _normalize(words[index]) if index < len(words) else None
    if key not in commands.BY_KEY:
        return ParsedInput(None, "")

    rest = words[index + 1:]
    native = bool(rest) and _normalize(rest[0]) == NATIVE
    return ParsedInput(key, " ".join(rest[1:] if native else rest).strip(), native)


async def read_input(message) -> dict:
    """Read the inbound message of a turn, from a distribution or a direct A2A call alike."""
    text = getattr(message, "text", None) if message is not None else None
    parsed = parse_input(text)
    return {"command": parsed.key, "native": parsed.native, "argument": parsed.argument, "input_text": text}


async def read_card_action(event) -> dict:
    """Read a button press on a card: a button's ``action_id`` is a command key."""
    action_id = getattr(event.payload, "action_id", None) if event and event.payload else None
    return {"command": parse_input(action_id).key, "native": False, "argument": "", "input_text": action_id}


def route(state: TourState) -> str:
    """The node that answers the turn.

    A command's node has its key as its name. ``<command> native`` runs
    ``<command>_native`` when the command has ``with_langgraph``, the command's
    own node when it already is LangGraph's own (``ask``, ``llm``), and
    ``not_native`` when LangGraph alone cannot do it. Input that matches
    nothing goes to the menu.
    """
    key = state.get("command")
    if key is None:
        return "help"
    module = commands.BY_KEY[key]
    if not state.get("native"):
        return key
    if hasattr(module, "with_langgraph"):
        return f"{key}_native"
    return "not_native" if module.COMMAND.no_native else key


async def not_native(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Say that LangGraph alone cannot do what the command shows, and which SDK call does it."""
    command = commands.BY_KEY[state["command"]].COMMAND
    thread = Thread.from_context(runtime.context)
    reply = await thread.reply(
        f"LangGraph alone cannot do this: {command.no_native}. Use `{command.api}`, as `{command.key}` shows."
        + command.footer
    )
    return {"messages": [reply]}


def _normalize(word: str) -> str:
    """Lower-case a word and drop punctuation, so `/Card.` matches `card`."""
    return _PUNCTUATION.sub("", word.lower())
