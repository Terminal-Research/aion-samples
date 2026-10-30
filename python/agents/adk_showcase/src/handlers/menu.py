"""The menu: a listing of every demonstration the agent offers, as a text artifact."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src.commands import menu_lines
from src.replies import with_footer

INTRO = (
    "I am a showcase agent. Every answer below is written by the agent itself, "
    "so what you see is platform behaviour rather than model output — except "
    "`llm`, where a model answers through the platform's model service. An "
    "answer is the task's result, so it arrives as a text artifact rather than "
    "as a message; send `card` when you want to see the rich-card rendering "
    "instead."
)

DEFAULT_TITLE = "Aion Showcase — ADK"
"""Title used when the turn carries no environment. The ``default`` of
``greeting`` in aion.yaml is applied by the control plane, not by the SDK, so a
direct local call needs the code's own copy."""


async def menu_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Show the menu, quoting input that named no command.

    The menu is the task's result, so it goes out as a text artifact and the
    task holds no message from the agent.

    Args:
        ctx: Invocation context of the current turn.
        argument: Text that matched no command — the whole line when nothing
            matched, or whatever followed the `help` keyword when it did.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    environment = ctx.aion_runtime_context.get_environment()
    title = (environment.get_configuration_variable("greeting") if environment else None) or DEFAULT_TITLE

    header: list[str] = []
    if argument.strip():
        header = [f'"{argument.strip()}" is not one of my commands.', ""]

    await thread.reply(
        text_artifact(
            with_footer(
                "help",
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
        )
    )
