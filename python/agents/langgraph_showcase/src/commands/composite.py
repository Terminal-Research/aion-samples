"""`composite`: one artifact sent in chunks as it is produced, like a long generated document.

The chunks share an artifact id: the first opens the artifact, the others
append to it, and the last one closes it.
"""

from __future__ import annotations

import uuid

from aion.core.a2a import file_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring import emit_artifact
from aion.langgraph.authoring.invocation import Thread
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="composite",
    summary="One artifact streamed in several appended chunks",
    api="emit_artifact(append=, is_last_chunk=)",
    no_native="LangGraph has no artifacts to send in chunks",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send three chunks with ``emit_artifact()``, then explain them in a message."""
    thread = Thread.from_context(runtime.context)
    writer = get_stream_writer()
    artifact_id = str(uuid.uuid4())
    chapters = ("Chapter one. ", "Chapter two. ", "Chapter three.")
    for index, chapter in enumerate(chapters):
        emit_artifact(
            writer,
            file_artifact(chapter.encode(), mime_type="text/plain", name="story.txt", artifact_id=artifact_id),
            append=index > 0,
            is_last_chunk=index == len(chapters) - 1,
        )
    reply = await thread.reply(f"`story.txt` arrived as {len(chapters)} chunks of one artifact." + COMMAND.footer)
    return {"messages": [reply]}


# No `with_langgraph`: LangGraph has no artifacts to send in chunks, and `composite native` says so.
