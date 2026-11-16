"""`metadata`: metadata of your own on a message and on an artifact.

Keys under ``aion:`` are reserved for the platform; anything else travels
untouched and comes back on the event the client receives.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import data_artifact
from google.adk.events import Event
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="metadata",
    summary="Metadata of your own on a message and on an artifact",
    api="thread.reply(metadata=...)",
    native="Event(custom_metadata=...), which lands in the message's metadata",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Pass ``metadata=`` to ``thread.reply()``, for a message and for an artifact."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply("This message carries metadata.", metadata={"showcase.step": "message", "showcase.run": "demo"})
    await thread.reply(data_artifact({"checked": True}, name="metadata_demo"), metadata={"showcase.step": "artifact"})
    await thread.reply(
        "The message keeps its metadata in `message.metadata`; the artifact's goes on its event." + COMMAND.footer
    )


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Set ``custom_metadata`` on a text event; it lands in the message's metadata."""
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text="This event carries metadata.")]),
        custom_metadata={"showcase.step": "message", "showcase.run": "demo"},
    )
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text="The event above carried its metadata into `message.metadata`.")]),
    )
