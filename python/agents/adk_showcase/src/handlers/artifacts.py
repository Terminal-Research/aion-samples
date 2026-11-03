"""Artifact demonstrations: hand-built, inline files, remote files, data, chunked delivery."""

from __future__ import annotations

import json
import uuid

from a2a.types import Artifact, Part
from aion.adk.authoring.invocation import AionInvocationContext, Thread, emit_artifact, get_adk_emitter
from aion.core.a2a import data_artifact, file_artifact, url_artifact

from src.replies import with_footer

REPORT = """date,region,units
2026-01-01,north,120
2026-01-01,south,98
"""

# A real, publicly reachable file: a sample that emits a dead link makes a
# working feature look broken.
REMOTE_FILE_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"

HAND_BUILT_NAME = "hand-built"
"""Name of the artifact the `artifact` command builds by hand."""

HAND_BUILT_METADATA = {"showcase.kind": "hand-built"}
"""Custom metadata of that artifact; keys outside ``aion:`` travel untouched."""


async def artifact_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send an artifact built field by field, then explain it in a message.

    Any artifact the agent sends is part of the task's result, whatever it
    carries. Building ``a2a.types.Artifact`` directly gives full control over
    its id, name, parts and metadata, and ``thread.reply()`` publishes it as
    it is; ``text_artifact()`` builds the common case — one text part, a
    fresh id, the name ``text`` — and is how the commands whose answer is
    text send it. The explanation describes the result rather than being
    one, so it is a message.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    artifact = Artifact(
        artifact_id=f"hand-built-{uuid.uuid4()}",
        name=HAND_BUILT_NAME,
        parts=[Part(text="This artifact was built by hand: its own id, a name, one text part and custom metadata.")],
        metadata=HAND_BUILT_METADATA,
    )
    await thread.reply(artifact)

    await thread.reply(
        with_footer(
            "artifact",
            f"The `{HAND_BUILT_NAME}` artifact, id `{artifact.artifact_id}`, holds one "
            "text part and the metadata `showcase.kind: hand-built`.",
            "",
            "Any artifact an agent sends is the task's result, whatever it holds. "
            "`text_artifact(text)` is the short way to build one for text: one text "
            "part, a fresh id and the name `text`. This explanation only describes "
            "the result, so it is a message.",
        )
    )


async def file_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send the same kind of attachment twice: inline bytes, then a URL.

    Inline bytes travel in the event itself and suit small results. A URL
    artifact references a file the client fetches on its own, which is what you
    want for anything large or already hosted. The files are the task's
    result; the explanation after them is a message.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        file_artifact(REPORT.encode(), mime_type="text/csv", name="units.csv")
    )
    await thread.reply(
        url_artifact(REMOTE_FILE_URL, mime_type="text/plain", name="rfc9110.txt")
    )

    await thread.reply(
        with_footer(
            "file",
            "Two file artifacts: `units.csv` carries its bytes inline, "
            "`rfc9110.txt` is a reference your client resolves itself.",
        )
    )


async def data_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send a structured result rather than prose, then explain it in a message."""
    thread = Thread.from_context(ctx.aion_runtime_context)

    payload = {
        "status": "ok",
        "totals": {"north": 120, "south": 98},
        "generated_by": "adk_showcase",
    }
    await thread.reply(data_artifact(payload, name="totals"))

    await thread.reply(
        with_footer(
            "data",
            "That artifact holds structured data, not text:",
            json.dumps(payload, indent=2),
            "",
            "A data part is a protobuf `Value`, so a client reads every number in it "
            "as a float: `120` arrives as `120.0`.",
        )
    )


async def composite_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Build one artifact out of several appended chunks.

    All chunks share an artifact id. ``append=True`` adds to what was already
    sent, and ``is_last_chunk=True`` closes the artifact — the same shape a
    long generated document takes as it is produced. ``emit_artifact`` takes
    the event emitter of the running invocation, which ``get_adk_emitter()``
    returns. The file is the task's result; the explanation after it is a
    message.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)
    emitter = get_adk_emitter()

    if emitter is None:
        await thread.reply(
            with_footer(
                "composite",
                "No event emitter is available outside an invocation, so there is "
                "nothing to append to.",
            )
        )
        return

    artifact_id = str(uuid.uuid4())
    chapters = ("Chapter one. ", "Chapter two. ", "Chapter three.")
    for index, chapter in enumerate(chapters):
        await emit_artifact(
            emitter,
            ctx,
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
        with_footer(
            "composite",
            f"`story.txt` arrived as {len(chapters)} chunks sharing one artifact id. "
            "The first opened it, the rest appended, and the last one closed it.",
        )
    )
