"""Artifact demonstrations: inline files, remote files, data, versioning."""

from __future__ import annotations

import json

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import data_artifact, file_artifact, url_artifact

from src.replies import with_footer

REPORT = """date,region,units
2026-01-01,north,120
2026-01-01,south,98
"""

# A real, publicly reachable file: a sample that emits a dead link makes a
# working feature look broken.
REMOTE_FILE_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"


async def file_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send the same kind of attachment twice: inline bytes, then a URL.

    Both go through the ADK artifact service, which stores the part and emits
    an event carrying the artifact delta.
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
    """Send a structured result rather than prose."""
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
        )
    )


async def composite_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Save one artifact name twice and let the store keep both versions.

    Artifacts go through the ADK artifact service, which owns their storage and
    versions them by filename: saving ``story.txt`` again does not extend the
    first one, it stores version 2 beside it. Use versions when a result is
    produced in successive drafts, and a single artifact when it is finished.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        file_artifact(b"Draft one.", mime_type="text/plain", name="story.txt")
    )
    await thread.reply(
        file_artifact(b"Draft one. Draft two.", mime_type="text/plain", name="story.txt")
    )

    await thread.reply(
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
