"""The menu: a plain-text listing of every demonstration the agent offers."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread

from src.commands import MENU_COMMAND, menu_lines
from src.replies import say

INTRO = (
    "I am a showcase agent. Every reply below is written by the agent itself, "
    "so what you see is platform behaviour rather than model output. Replies "
    "are plain text; send `card` when you want to see the rich-card rendering "
    "instead."
)

DEFAULT_TITLE = "Aion Showcase — ADK"


async def menu_handler(ctx: AionInvocationContext, unrecognized: str | None = None) -> None:
    """Show the menu, quoting the input when it matched no command."""
    thread = Thread.from_context(ctx.aion_runtime_context)

    # `greeting` is declared in aion.yaml and set per environment; it is absent
    # on a direct local call, which is what the default covers.
    environment = ctx.aion_runtime_context.get_environment()
    title = (environment.get_configuration_variable("greeting") if environment else None) or DEFAULT_TITLE

    header: list[str] = []
    if unrecognized:
        header = [f'"{unrecognized.strip()}" is not one of my commands.', ""]

    await say(
        thread,
        MENU_COMMAND,
        *header,
        title,
        "",
        INTRO,
        "",
        "Commands:",
        *menu_lines(),
        "",
        "Keywords are case-insensitive and tolerate a leading verb, so "
        '"card", "Show me the card" and "/card" all work.',
    )
