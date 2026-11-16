"""`artifact`: a result built field by field from ``a2a.types.Artifact``.

An artifact is a task's result. ``text_artifact(text)`` builds the common
text case in one call; building one by hand sets its own id, name, parts and
metadata.
"""

from __future__ import annotations

import uuid

from a2a.types import Artifact, Part
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="artifact",
    summary="An artifact built by hand: its own id, name, text and metadata",
    api="thread.reply(Artifact(...))",
    no_native="LangGraph has no artifacts",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send the artifact with ``thread.reply()``, then explain it in a message."""
    thread = Thread.from_context(runtime.context)
    artifact = Artifact(
        artifact_id=f"hand-built-{uuid.uuid4()}",
        name="hand-built",
        parts=[Part(text="This artifact was built field by field: its own id, a name, one text part and metadata.")],
        metadata={"showcase.kind": "hand-built"},
    )
    await thread.reply(artifact)
    reply = await thread.reply(
        f"That artifact is the task's result, with the id `{artifact.artifact_id}`. "
        "For plain text, `text_artifact(text)` builds one in a call." + COMMAND.footer
    )
    return {"messages": [reply]}


# No `with_langgraph`: LangGraph has no artifacts, and `artifact native` says so.
