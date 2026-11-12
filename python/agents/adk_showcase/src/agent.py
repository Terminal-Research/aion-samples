"""The tour's agent: it reads the keyword of each turn and runs that command."""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext
from google.adk.agents import BaseAgent
from google.adk.events import Event
from typing_extensions import override

from src.commands import BY_KEY, ask, help, llm
from src.tour.routing import inbound_text, not_native, parse_input


class ShowcaseAgent(BaseAgent):
    """Runs one command per turn: ``with_sdk``, or ``with_adk`` for ``<command> native``."""

    @override
    async def _run_async_impl(self, ctx: AionInvocationContext) -> AsyncGenerator[Event, None]:
        # A turn that resumes `ask` carries the answer to the call the run
        # paused on, not a new command.
        reply = ask.answered_question(ctx)
        if reply is not None:
            await ask.answer(ctx, reply)
            return

        text = inbound_text(ctx)
        parsed = parse_input(text)
        if parsed.key is None:
            await help.with_sdk(ctx, text)
            return

        command = BY_KEY[parsed.key]
        if not parsed.native:
            result = command.with_sdk(ctx, parsed.argument)
        elif hasattr(command, "with_adk"):
            result = command.with_adk(ctx, parsed.argument)
        elif command.COMMAND.no_native:
            result = not_native(ctx, parsed.key)
        else:
            # `ask` and `llm` already are ADK's own: `native` runs them as they are.
            result = command.with_sdk(ctx, parsed.argument)

        # A command is a coroutine to await, or an async generator of ADK events to forward.
        if inspect.isasyncgen(result):
            async for event in result:
                yield event
        else:
            await result


def create_agent() -> ShowcaseAgent:
    """Build the agent; the Aion server runs it.

    The `llm` command's ``LlmAgent`` is declared in ``sub_agents``, so ADK
    knows the agents that answer in this conversation: a turn after `llm`
    comes back to the showcase.
    """
    return ShowcaseAgent(
        name="showcase",
        description="Guided tour of the Aion platform features, built with Google ADK",
        sub_agents=[llm.build_agent()],
    )
