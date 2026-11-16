"""`help`: the menu of every command, as a text artifact."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src.tour import Command
from src.tour.menu import menu_lines

COMMAND = Command(
    key="help",
    summary="This menu",
    api="thread.reply(text_artifact(text))",
)

INTRO = (
    "I am a showcase agent. Every command shows one platform feature and names the SDK call "
    "behind it; the answers are written by the agent itself, except `llm`, where a model answers."
)

DEFAULT_TITLE = "Aion Showcase — ADK"
"""The title when the turn carries no environment: the control plane, not the
SDK, applies the ``default`` of ``greeting`` in aion.yaml."""


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Show the menu, quoting ``argument`` when it is input that matched no command."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    environment = ctx.aion_runtime_context.get_environment()
    title = (environment.get_configuration_variable("greeting") if environment else None) or DEFAULT_TITLE
    header = [f'"{argument.strip()}" is not one of my commands.', ""] if argument.strip() else []
    menu = "\n".join(
        [
            *header,
            title,
            "",
            INTRO,
            "",
            "Commands:",
            *menu_lines(),
            "",
            "Add `native` after a command to see it done with ADK alone, e.g. `stream native`. "
            "Every command is the file src/commands/<command>.py.",
        ]
    )
    await thread.reply(text_artifact(menu + COMMAND.footer))
