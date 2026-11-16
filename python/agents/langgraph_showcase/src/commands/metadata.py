"""`metadata`: metadata of your own on a message and on an artifact.

Keys under ``aion:`` are reserved for the platform; anything else travels
untouched and comes back on the event the client receives.
"""

from __future__ import annotations

from aion.core.a2a import data_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="metadata",
    summary="Metadata of your own on a message and on an artifact",
    api="thread.reply(metadata=...)",
    no_native="an AIMessage's additional_kwargs do not reach the client",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Pass ``metadata=`` to ``thread.reply()``, for a message and for an artifact."""
    thread = Thread.from_context(runtime.context)
    await thread.reply("This message carries metadata.", metadata={"showcase.step": "message", "showcase.run": "demo"})
    await thread.reply(data_artifact({"checked": True}, name="metadata_demo"), metadata={"showcase.step": "artifact"})
    reply = await thread.reply(
        "The message keeps its metadata in `message.metadata`; the artifact's goes on its event." + COMMAND.footer
    )
    return {"messages": [reply]}


# No `with_langgraph`: an AIMessage's additional_kwargs do not reach the client, and `metadata native` says so.
