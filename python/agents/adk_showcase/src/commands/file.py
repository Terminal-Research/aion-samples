"""`file`: files as a result, one with its bytes inline and one as a link.

With the SDK a file is an artifact of the task. ADK saves a file the same way
it saves any artifact: ``save_artifact()`` with an ``inline_data`` part.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import file_artifact, url_artifact
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="file",
    summary="File artifacts: inline bytes and a remote URL",
    api="file_artifact() / url_artifact()",
    native="save_artifact() with an inline_data part",
)

REPORT = """date,region,units
2026-01-01,north,120
2026-01-01,south,98
"""

# A real, reachable file: a sample that emits a dead link makes a working feature look broken.
REMOTE_FILE_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Send two file artifacts with ``thread.reply()``, then explain them in a message."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply(file_artifact(REPORT.encode(), mime_type="text/csv", name="units.csv"))
    await thread.reply(url_artifact(REMOTE_FILE_URL, mime_type="text/plain", name="rfc9110.txt"))
    await thread.reply(
        "`units.csv` carries its bytes inline; `rfc9110.txt` is a link your client resolves." + COMMAND.footer
    )


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Save the file with ``save_artifact()``; the event that records the save publishes it."""
    actions = EventActions()
    await CallbackContext(ctx, event_actions=actions).save_artifact(
        "units.csv", types.Part(inline_data=types.Blob(mime_type="text/csv", data=REPORT.encode()))
    )
    yield Event(invocation_id=ctx.invocation_id, author=ctx.agent.name, actions=actions)
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text="That artifact is `units.csv`, its bytes inline.")]),
    )
