"""Command registry — the single source of truth for the showcase agent.

Everything the agent exposes is derived from ``COMMANDS``: the handler table,
the menu, the response footers, and the ``skills.examples`` list in
``aion.yaml``. Adding a demonstration means adding one entry here and one
handler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """One demonstration exposed by the agent.

    Attributes:
        key: Canonical keyword the user types.
        summary: One-line description shown in the menu.
        api: SDK call this command demonstrates, shown in the response footer.
        source: Path to the file implementing it, shown in the response footer.
        argument_hint: Name of the free-form text this command accepts after
            its keyword, or None when the keyword is the whole command.
    """

    key: str
    summary: str
    api: str
    source: str
    argument_hint: str | None = None

    @property
    def usage(self) -> str:
        """Return the command as the menu spells it, argument included."""
        return f"{self.key} {{{self.argument_hint}}}" if self.argument_hint else self.key

    def footer(self) -> str:
        """Return the trailing line that points at the API and the source file."""
        return f"↳ {self.api} · {self.source}"


COMMANDS: tuple[Command, ...] = (
    Command(
        key="help",
        summary="This menu, as plain text",
        api="thread.reply(text)",
        source="src/handlers/menu.py",
    ),
    Command(
        key="stream",
        summary="A single reply streamed in chunks as it is produced",
        api="thread.reply(async iterator)",
        source="src/handlers/messaging.py",
    ),
    Command(
        key="typing",
        summary="Ephemeral typing indicator that is never persisted",
        api="thread.typing()",
        source="src/handlers/messaging.py",
    ),
    Command(
        key="card",
        summary="Rich card, composed from components and referenced by URL",
        api="Card / Text / Fields / Actions",
        source="src/handlers/cards.py",
    ),
    Command(
        key="file",
        summary="File artifacts: inline bytes and a remote URL",
        api="file_artifact() / url_artifact()",
        source="src/handlers/artifacts.py",
    ),
    Command(
        key="data",
        summary="Structured data artifact",
        api="data_artifact()",
        source="src/handlers/artifacts.py",
    ),
    Command(
        key="composite",
        summary="One artifact saved twice, so the store keeps both versions",
        api="artifact_service versioning",
        source="src/handlers/artifacts.py",
    ),
    Command(
        key="ask",
        summary="Agent asks for missing input and picks it up on the next turn",
        api="EventActions(state_delta=...)",
        source="src/handlers/hitl.py",
    ),
    Command(
        key="react",
        summary="Reaction added to, then removed from, your message",
        api="message.react()",
        source="src/handlers/messaging.py",
    ),
    Command(
        key="metadata",
        summary="Custom metadata attached to a message and to an artifact",
        api="metadata= on reply() and artifacts",
        source="src/handlers/messaging.py",
    ),
    Command(
        key="progress",
        summary="Long-running work reporting progress before it finishes",
        api="thread.typing() during work",
        source="src/handlers/tasks.py",
    ),
    Command(
        key="task",
        summary="Explicit A2A Task placed in the outbox",
        api="A2AOutbox(task=...)",
        source="src/handlers/tasks.py",
    ),
    Command(
        key="message",
        summary="Explicit A2A Message placed in the outbox",
        api="A2AOutbox(message=...)",
        source="src/handlers/tasks.py",
    ),
    Command(
        key="fail",
        summary="Task finished in the failed state",
        api="TaskState.TASK_STATE_FAILED",
        source="src/handlers/tasks.py",
    ),
    Command(
        key="context",
        summary="What the agent knows about this conversation and caller",
        api="Thread.from_context() / context.inbox",
        source="src/handlers/context.py",
    ),
    Command(
        key="config",
        summary="Configuration values the control plane passed to this deployment",
        api="context.get_environment()",
        source="src/handlers/config.py",
    ),
    Command(
        key="http",
        summary="Custom HTTP routes this agent serves next to A2A",
        api="app_registry.add_router()",
        source="src/api.py",
    ),
)

COMMANDS_BY_KEY: dict[str, Command] = {command.key: command for command in COMMANDS}

MENU_COMMAND = COMMANDS_BY_KEY["help"]

_FILLER_WORDS = frozenset({"show", "demo", "run", "do", "me", "the", "a", "an", "please"})
_PUNCTUATION = re.compile(r"[^\w\s-]")


@dataclass(frozen=True)
class ParsedInput:
    """A resolved command and the free-form text that followed it."""

    command: Command | None
    argument: str


def _normalize(word: str) -> str:
    """Lower-case a word and drop punctuation, so `/Card.` matches `card`."""
    return _PUNCTUATION.sub("", word.lower())


def parse_input(text: str | None) -> ParsedInput:
    """Resolve free-form user input to a command and its argument.

    Each command has exactly one keyword. The first meaningful word selects it;
    everything after that is the argument, kept verbatim so a prompt reaches
    the model exactly as typed. Matching is case-insensitive and tolerates a
    leading verb, so ``card``, ``Show me the card`` and ``/card`` all select
    the same command.

    Args:
        text: Raw inbound message text, or None when the turn carries no text.

    Returns:
        The matching command and its argument. ``command`` is None when the
        input matches nothing, which sends the turn to the menu.
    """
    if not text:
        return ParsedInput(None, "")

    words = text.split()
    index = 0
    while index < len(words) and _normalize(words[index]) in _FILLER_WORDS:
        index += 1
    if index >= len(words):
        return ParsedInput(None, "")

    command = COMMANDS_BY_KEY.get(_normalize(words[index]))
    if command is None:
        return ParsedInput(None, "")

    return ParsedInput(command, " ".join(words[index + 1:]).strip())


def parse_command(text: str | None) -> Command | None:
    """Resolve input to a command, ignoring any argument."""
    return parse_input(text).command


def menu_lines() -> list[str]:
    """Return the menu as plain-text lines, one per command."""
    width = max(len(command.usage) for command in COMMANDS)
    return [f"  {command.usage.ljust(width)}  {command.summary}" for command in COMMANDS]


def examples() -> list[str]:
    """Return the canonical inputs, for the skills.examples list in aion.yaml."""
    return [
        f"{command.key} What is the A2A protocol?" if command.argument_hint else command.key
        for command in COMMANDS
    ]
