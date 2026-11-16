"""`help`: the menu of every command, as a text artifact."""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState
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

DEFAULT_TITLE = "Aion Showcase — LangGraph"
"""The title when the turn carries no environment: the control plane, not the
SDK, applies the ``default`` of ``greeting`` in aion.yaml."""


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Show the menu, quoting the input when it matched no command."""
    thread = Thread.from_context(runtime.context)
    environment = runtime.context.get_environment()
    title = (environment.get_configuration_variable("greeting") if environment else None) or DEFAULT_TITLE
    unrecognized = state.get("input_text") if state.get("command") is None else None
    header = [f'"{unrecognized.strip()}" is not one of my commands.', ""] if unrecognized else []
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
            "Add `native` after a command to see it done with LangGraph alone, e.g. `stream native`. "
            "Every command is the file src/commands/<command>.py.",
        ]
    )
    await thread.reply(text_artifact(menu + COMMAND.footer))
    return {}
