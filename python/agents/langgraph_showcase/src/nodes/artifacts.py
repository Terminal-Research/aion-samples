"""Artifact demonstrations: inline files, remote files, data, chunked delivery."""

from __future__ import annotations

import json
import uuid

from aion.core.a2a import data_artifact, file_artifact, url_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring import emit_artifact
from aion.langgraph.authoring.invocation import Thread
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from src.commands import COMMANDS_BY_KEY
from src.replies import say
from src.state import AgentState

FILE = COMMANDS_BY_KEY["file"]
DATA = COMMANDS_BY_KEY["data"]
COMPOSITE = COMMANDS_BY_KEY["composite"]

REPORT = """date,region,units
2026-01-01,north,120
2026-01-01,south,98
"""

# A real, publicly reachable file: a sample that emits a dead link makes a
# working feature look broken.
REMOTE_FILE_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"


async def file_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send the same kind of attachment twice: inline bytes, then a URL.

    Inline bytes travel in the event itself and suit small results. A URL
    artifact references a file the client fetches on its own, which is what you
    want for anything large or already hosted.
    """
    thread = Thread.from_context(runtime.context)

    await thread.reply(
        file_artifact(REPORT.encode(), mime_type="text/csv", name="units.csv")
    )
    await thread.reply(
        url_artifact(REMOTE_FILE_URL, mime_type="text/plain", name="rfc9110.txt")
    )

    return await say(
        thread,
        FILE,
        "Two file artifacts: `units.csv` carries its bytes inline, "
        "`rfc9110.txt` is a reference your client resolves itself.",
    )


async def data_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send a structured result rather than prose.

    A data artifact keeps the result machine-readable, which is what another
    agent needs when it consumes this one.
    """
    thread = Thread.from_context(runtime.context)

    payload = {
        "status": "ok",
        "totals": {"north": 120, "south": 98},
        "generated_by": "langgraph_showcase",
    }
    await thread.reply(data_artifact(payload, name="totals"))

    return await say(
        thread,
        DATA,
        "That artifact holds structured data, not text:",
        json.dumps(payload, indent=2),
    )


async def composite_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Build one artifact out of several appended chunks.

    All chunks share an artifact id. ``append=True`` adds to what was already
    sent, and ``is_last_chunk=True`` closes the artifact — the same shape a
    long generated document takes as it is produced.
    """
    thread = Thread.from_context(runtime.context)
    writer = get_stream_writer()

    if writer is None:
        return await say(
            thread,
            COMPOSITE,
            "No stream writer is available outside an invocation, so there is "
            "nothing to append to.",
        )

    artifact_id = str(uuid.uuid4())
    chapters = ("Chapter one. ", "Chapter two. ", "Chapter three.")
    for index, chapter in enumerate(chapters):
        emit_artifact(
            writer,
            file_artifact(
                chapter.encode(),
                mime_type="text/plain",
                name="story.txt",
                artifact_id=artifact_id,
            ),
            append=index > 0,
            is_last_chunk=index == len(chapters) - 1,
        )

    return await say(
        thread,
        COMPOSITE,
        f"`story.txt` arrived as {len(chapters)} chunks sharing one artifact id. "
        "The first opened it, the rest appended, and the last one closed it.",
    )
