"""Artifact demonstrations: a hand-built artifact, files, data, chunked delivery."""

from __future__ import annotations

import json
import uuid

from a2a.types import Artifact, Part
from aion.core.a2a import data_artifact, file_artifact, text_artifact, url_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring import emit_artifact
from aion.langgraph.authoring.invocation import Thread
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from src.replies import with_footer
from src.state import AgentState

REPORT = """date,region,units
2026-01-01,north,120
2026-01-01,south,98
"""

# A real, publicly reachable file: a sample that emits a dead link makes a
# working feature look broken.
REMOTE_FILE_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"

HAND_BUILT_NAME = "hand-built"
HAND_BUILT_METADATA = {"showcase.kind": "hand-built"}


async def artifact_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send an artifact built field by field, then explain it in a second one.

    Any artifact the agent sends is part of the task's result, whatever it
    carries. Building ``a2a.types.Artifact`` directly gives full control over
    its id, name, parts and metadata; ``text_artifact()`` builds the common
    case — one text part, a fresh id, the name ``text`` — and is how every
    other command of this agent sends its answer.
    """
    thread = Thread.from_context(runtime.context)

    hand_built = Artifact(
        artifact_id=f"hand-built-{uuid.uuid4()}",
        name=HAND_BUILT_NAME,
        parts=[
            Part(
                text="This artifact was built field by field from `a2a.types.Artifact`: "
                "its own artifact id, a name, one text part and custom metadata."
            )
        ],
        metadata=HAND_BUILT_METADATA,
    )
    await thread.reply(hand_built)

    await thread.reply(
        text_artifact(
            with_footer(
                "artifact",
                "Two artifacts went out, and both are this task's result. The first "
                f"was built by hand: the id `{hand_built.artifact_id}`, the name "
                f"`{HAND_BUILT_NAME}`, one text part and the metadata "
                "`showcase.kind = hand-built`. This one came from `text_artifact()`.",
                "",
                "Whatever an artifact carries — text, a file, data — it is the task's "
                "result. `text_artifact(text)` is the short way to build the common "
                "text case, and it is how every other command here sends its answer.",
            )
        )
    )
    return {}


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

    await thread.reply(
        text_artifact(
            with_footer(
                "file",
                "Two file artifacts: `units.csv` carries its bytes inline, "
                "`rfc9110.txt` is a reference your client resolves itself.",
            )
        )
    )
    return {}


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

    await thread.reply(
        text_artifact(
            with_footer(
                "data",
                "That artifact holds structured data, not text:",
                json.dumps(payload, indent=2),
            )
        )
    )
    return {}


async def composite_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Build one artifact out of several appended chunks.

    All chunks share an artifact id. ``append=True`` adds to what was already
    sent, and ``is_last_chunk=True`` closes the artifact — the same shape a
    long generated document takes as it is produced.
    """
    thread = Thread.from_context(runtime.context)
    writer = get_stream_writer()

    if writer is None:
        await thread.reply(
            text_artifact(
                with_footer(
                    "composite",
                    "No stream writer is available outside an invocation, so there is "
                    "nothing to append to.",
                )
            )
        )
        return {}

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

    await thread.reply(
        text_artifact(
            with_footer(
                "composite",
                f"`story.txt` arrived as {len(chapters)} chunks sharing one artifact id. "
                "The first opened it, the rest appended, and the last one closed it.",
            )
        )
    )
    return {}
