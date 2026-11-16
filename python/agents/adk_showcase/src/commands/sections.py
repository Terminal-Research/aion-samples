"""`sections`: two streamed sections in one turn, as when a model answers, calls a tool and answers again.

Each section starts the task's ``aion:stream-delta`` artifact over: the client
sees both on the stream, and the task keeps only the last.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from google.adk.events import Event
from google.genai import types

from src.tour import Command, stream_text

COMMAND = Command(
    key="sections",
    summary="Two streamed sections in one turn; the task keeps the last",
    api="thread.reply(async iterator), twice",
    native="every run of partial events in a turn streams a section of its own",
)

FIRST_SECTION = "Let me check that with a tool."
SECOND_SECTION = "The tool came back, and this second section is the answer."
EXPLAINED = "Two sections were streamed. The task keeps only the second: a new section starts `aion:stream-delta` over."


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Stream two sections with ``thread.reply()``, a thought between them, then explain in a message."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply(stream_text(FIRST_SECTION))
    await thread.thinking("Calling a tool…")
    await thread.reply(stream_text(SECOND_SECTION))
    await thread.reply(EXPLAINED + COMMAND.footer)


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Yield two runs of partial events, each closed by the whole text, then a text event that explains."""
    for section in (FIRST_SECTION, SECOND_SECTION):
        words = section.split(" ")
        for index, word in enumerate(words):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=ctx.agent.name,
                partial=True,
                content=types.Content(role="model", parts=[types.Part(text=word if index == 0 else f" {word}")]),
            )
        yield Event(
            invocation_id=ctx.invocation_id,
            author=ctx.agent.name,
            content=types.Content(role="model", parts=[types.Part(text=section)]),
        )
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text=EXPLAINED)]),
    )
