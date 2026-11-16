"""`artifact`: a result kept as an artifact of the task.

With the SDK the artifact is built field by field from ``a2a.types.Artifact``:
its own id, name, parts and metadata. ADK keeps artifacts of its own through
``save_artifact()``, which saves a new version of the artifact every time.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from a2a.types import Artifact, Part
from aion.adk.authoring.invocation import AionInvocationContext, Thread
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="artifact",
    summary="An artifact built by hand: its own id, name, text and metadata",
    api="thread.reply(Artifact(...))",
    native="save_artifact(), which keeps a version of the artifact per save",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Send the artifact with ``thread.reply()``, then explain it in a message."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    artifact = Artifact(
        artifact_id=f"hand-built-{uuid.uuid4()}",
        name="hand-built",
        parts=[Part(text="This artifact was built field by field: its own id, a name, one text part and metadata.")],
        metadata={"showcase.kind": "hand-built"},
    )
    await thread.reply(artifact)
    await thread.reply(
        f"That artifact is the task's result, with the id `{artifact.artifact_id}`. "
        "For plain text, `text_artifact(text)` builds one in a call." + COMMAND.footer
    )


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Save the artifact with ``save_artifact()``; the event that records the save publishes it."""
    actions = EventActions()
    await CallbackContext(ctx, event_actions=actions).save_artifact(
        "report", types.Part(text="Saved through ADK's artifact service.")
    )
    yield Event(invocation_id=ctx.invocation_id, author=ctx.agent.name, actions=actions)
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text="That artifact is `report`, version 0.")]),
    )
