"""Artifact demonstrations: hand-built, inline files, remote files, data, versioning."""

from __future__ import annotations

import json
import uuid

from a2a.types import Artifact, Part
from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import data_artifact, file_artifact, text_artifact, url_artifact

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
    """Build an artifact field by field and send it as the task's result.

    Any artifact the agent sends is a result of the task, whatever it holds;
    the server copies no ``aion:assistant-answer`` for a task that has one.
    This one is assembled by hand: an id the agent chose, a name and one text
    part. ``thread.reply()`` saves the part to the ADK artifact service and
    the id and name travel with the event that announces it; the artifact's
    custom metadata is the ``metadata`` of that call, which the SDK merges
    into the metadata of the artifact the client receives.

    ``text_artifact(text)`` builds the same shape for plain text — one text
    part, a fresh id and the name ``text`` — and is how every other answer of
    this agent is sent, the explanation below included.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    artifact = Artifact(
        artifact_id=f"hand-built-{uuid.uuid4()}",
        name=HAND_BUILT_NAME,
        parts=[Part(text="This artifact was built by hand: its own id, a name and one text part.")],
    )
    await thread.reply(artifact, metadata=HAND_BUILT_METADATA)

    await thread.reply(
        text_artifact(
            with_footer(
                "artifact",
                f"The `{HAND_BUILT_NAME}` artifact, id `{artifact.artifact_id}`, holds one "
                "text part and the metadata `showcase.kind: hand-built`.",
                "",
                "Any artifact an agent sends is the task's result, whatever it holds. "
                "`text_artifact(text)` is the short way to build one for text: one text "
                "part, a fresh id and the name `text`. Every other answer of this agent, "
                "this one included, is sent that way.",
            )
        )
    )


async def file_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send the same kind of attachment twice: inline bytes, then a URL.

    Both go through the ADK artifact service, which stores the part and emits
    an event carrying the artifact delta. The explanation is a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

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


async def data_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send a structured result rather than prose, then explain it as text."""
    thread = Thread.from_context(ctx.aion_runtime_context)

    payload = {
        "status": "ok",
        "totals": {"north": 120, "south": 98},
        "generated_by": "adk_showcase",
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


async def composite_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Save one artifact name twice and let the store keep both versions.

    Artifacts go through the ADK artifact service, which owns their storage and
    versions them by filename: saving ``story.txt`` again does not extend the
    first one, it stores version 2 beside it. Use versions when a result is
    produced in successive drafts, and a single artifact when it is finished.
    The explanation is a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        file_artifact(b"Draft one.", mime_type="text/plain", name="story.txt")
    )
    await thread.reply(
        file_artifact(b"Draft one. Draft two.", mime_type="text/plain", name="story.txt")
    )

    await thread.reply(
        text_artifact(
            with_footer(
                "composite",
                "`story.txt` was saved twice, so the artifact service now holds two "
                "versions of it: the second save stored version 2 rather than "
                "extending version 1.",
                "",
                "The artifact service owns storage here, so versioning is how you say "
                "'here is more' — send the same name again and the client can still "
                "reach what came before.",
            )
        )
    )
