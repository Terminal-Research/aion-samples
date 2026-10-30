"""The menu: a plain-text listing of every demonstration the agent offers."""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.commands import menu_lines
from src.replies import with_footer
from src.state import AgentState

INTRO = (
    "I am a showcase agent. Every answer below is written by the agent itself, "
    "so what you see is platform behaviour rather than model output — except "
    "`llm`, where a model answers through the platform's model service. What "
    "a command produces is the task's result, an artifact — a text artifact "
    "when the answer is text — and text around a result is a message; send "
    "`card` when you want to see the rich-card rendering instead."
)

DEFAULT_TITLE = "Aion Showcase — LangGraph"
"""Title used when the turn carries no environment. The ``default`` of
``greeting`` in aion.yaml is applied by the control plane, not by the SDK, so a
direct local call needs the code's own copy."""


async def menu_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Show the menu, quoting the input when it matched no command."""
    thread = Thread.from_context(runtime.context)

    environment = runtime.context.get_environment()
    title = (environment.get_configuration_variable("greeting") if environment else None) or DEFAULT_TITLE

    header: list[str] = []
    unrecognized = state.get("input_text") if state.get("command") is None else None
    if unrecognized:
        header = [f'"{unrecognized.strip()}" is not one of my commands.', ""]

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
    return {}
