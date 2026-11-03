"""What a turn asks for: the keyword and ``native``, read from the message or a card button."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src import commands

NATIVE = "native"
"""The word after a keyword that asks for ADK's own way."""

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
    card`` and ``/card`` all select it; ``native`` right after it asks for ADK's
    own way; the rest is the argument, kept verbatim.
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


def inbound_text(ctx: AionInvocationContext) -> str:
    """The text of the turn, or the ``action_id`` of the card button that was pressed.

    A button's ``action_id`` is a command key, so pressing it runs the same
    command as typing that keyword.
    """
    runtime = ctx.aion_runtime_context
    if runtime is None:
        return ""
    event = runtime.event
    action_id = getattr(event.payload, "action_id", None) if event and event.payload else None
    if action_id:
        return action_id
    thread = Thread.from_context(runtime)
    return thread.message.text if thread.message else ""


async def not_native(ctx: AionInvocationContext, key: str) -> None:
    """Say that ADK alone cannot do what the command shows, and which SDK call does it."""
    command = commands.BY_KEY[key].COMMAND
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply(
        text_artifact(
            f"ADK alone cannot do this: {command.no_native}. Use `{command.api}`, as `{command.key}` shows."
            + command.footer
        )
    )


def _normalize(word: str) -> str:
    """Lower-case a word and drop punctuation, so `/Card.` matches `card`."""
    return _PUNCTUATION.sub("", word.lower())
