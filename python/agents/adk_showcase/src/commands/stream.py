"""`stream`: an answer that reaches the client in chunks while it is written.

The chunks are the task's ``aion:stream-delta`` artifact; when the task
finishes, the server joins them into one text.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from google.adk.events import Event
from google.genai import types

from src.tour import Command, stream_text

COMMAND = Command(
    key="stream",
    summary="An answer streamed in chunks as it is written",
    api="thread.reply(async iterator)",
    native="Event(partial=True) for every chunk, then one event with the whole text",
)

ANSWER = "This answer reached you in chunks, the way a model's tokens arrive."


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Hand ``thread.reply()`` any async iterator of text; every item goes out as a chunk."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply(stream_text(ANSWER + COMMAND.footer))


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Yield a partial event for every chunk, then one event with the whole text."""
    words = ANSWER.split(" ")
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
        content=types.Content(role="model", parts=[types.Part(text=ANSWER)]),
    )
