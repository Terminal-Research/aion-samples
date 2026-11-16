"""`composite`: one artifact sent in chunks as it is produced, like a long generated document.

The chunks share an artifact id: the first opens the artifact, the others
append to it, and the last one closes it.
"""

from __future__ import annotations

import uuid

from aion.adk.authoring.invocation import AionInvocationContext, Thread, emit_artifact, get_adk_emitter
from aion.core.a2a import file_artifact

from src.tour import Command

COMMAND = Command(
    key="composite",
    summary="One artifact streamed in several appended chunks",
    api="emit_artifact(append=, is_last_chunk=)",
    no_native="save_artifact() replaces an artifact whole, it has no chunks",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Send three chunks with ``emit_artifact()`` through the invocation's emitter, then explain them."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    emitter = get_adk_emitter()
    artifact_id = str(uuid.uuid4())
    chapters = ("Chapter one. ", "Chapter two. ", "Chapter three.")
    for index, chapter in enumerate(chapters):
        await emit_artifact(
            emitter,
            ctx,
            file_artifact(chapter.encode(), mime_type="text/plain", name="story.txt", artifact_id=artifact_id),
            append=index > 0,
            is_last_chunk=index == len(chapters) - 1,
        )
    await thread.reply(f"`story.txt` arrived as {len(chapters)} chunks of one artifact." + COMMAND.footer)


# No `with_adk`: save_artifact() replaces an artifact whole, and `composite native` says so.
