"""Agent assembly for the showcase agent.

Dispatch is generated from the command registry: every entry in
``src.commands.COMMANDS`` maps to one handler. Adding a demonstration means
adding a registry entry and a handler — the menu, the HTTP listing and the
agent card examples follow from the same source.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Callable

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.server import app_registry
from google.adk.agents import BaseAgent
from google.adk.events import Event
from typing_extensions import override

from src.api import router as http_router
from src.commands import parse_input
from src.handlers import (
    answer_handler,
    ask_handler,
    card_handler,
    composite_handler,
    config_handler,
    context_handler,
    data_handler,
    fail_handler,
    file_handler,
    http_handler,
    is_awaiting_answer,
    menu_handler,
    message_handler,
    metadata_handler,
    progress_handler,
    react_handler,
    stream_handler,
    task_handler,
    typing_handler,
)

HANDLERS: dict[str, Callable] = {
    "help": menu_handler,
    "stream": stream_handler,
    "typing": typing_handler,
    "card": card_handler,
    "file": file_handler,
    "data": data_handler,
    "composite": composite_handler,
    "ask": ask_handler,
    "react": react_handler,
    "metadata": metadata_handler,
    "progress": progress_handler,
    "task": task_handler,
    "message": message_handler,
    "fail": fail_handler,
    "context": context_handler,
    "config": config_handler,
    "http": http_handler,
}


def _inbound_text(ctx: AionInvocationContext) -> str:
    """Return the text of the inbound turn, or the pressed card button's id.

    Card buttons carry a developer-defined ``action_id``. This agent uses the
    command key as the action id, so a press is handled exactly like typing
    that keyword.
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


class ShowcaseAgent(BaseAgent):
    """Routes one keyword per turn to the demonstration it names."""

    @override
    async def _run_async_impl(
        self,
        ctx: AionInvocationContext,
    ) -> AsyncGenerator[Event, None]:
        text = _inbound_text(ctx)

        # An open question takes precedence: this turn carries its answer, not
        # a new command. ADK ends the turn when it asks, so session state is
        # what links the two turns together.
        if is_awaiting_answer(ctx):
            async for event in answer_handler(ctx, text):
                yield event
            return

        parsed = parse_input(text)
        if parsed.command is None:
            await menu_handler(ctx, unrecognized=text)
            return

        # Only commands that declare an argument hint are handed the rest of
        # the line; everything else takes the context alone.
        handler = HANDLERS[parsed.command.key]
        result = handler(ctx, parsed.argument) if parsed.command.argument_hint else handler(ctx)
        if inspect.isasyncgen(result):
            async for event in result:
                yield event
        else:
            await result


def create_agent() -> ShowcaseAgent:
    """Build the showcase agent."""
    return ShowcaseAgent(
        name="showcase",
        description="Guided tour of the Aion platform features, built with Google ADK",
    )


app_registry.add_router(http_router)
