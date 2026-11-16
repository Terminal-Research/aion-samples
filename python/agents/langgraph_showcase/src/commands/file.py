"""`file`: files as a result, one with its bytes inline and one as a link.

With the SDK a file is an artifact of the task. LangGraph alone has no
artifacts, but a file block in an AIMessage reaches the client as part of
that message.
"""

from __future__ import annotations

import base64

from aion.core.a2a import file_artifact, url_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="file",
    summary="File artifacts: inline bytes and a remote URL",
    api="file_artifact() / url_artifact()",
    native="a file block in an AIMessage, which arrives as part of a message",
)

REPORT = """date,region,units
2026-01-01,north,120
2026-01-01,south,98
"""

# A real, reachable file: a sample that emits a dead link makes a working feature look broken.
REMOTE_FILE_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send two file artifacts with ``thread.reply()``, then explain them in a message."""
    thread = Thread.from_context(runtime.context)
    await thread.reply(file_artifact(REPORT.encode(), mime_type="text/csv", name="units.csv"))
    await thread.reply(url_artifact(REMOTE_FILE_URL, mime_type="text/plain", name="rfc9110.txt"))
    reply = await thread.reply(
        "`units.csv` carries its bytes inline; `rfc9110.txt` is a link your client resolves." + COMMAND.footer
    )
    return {"messages": [reply]}


async def with_langgraph(state: TourState) -> dict:
    """Return an AIMessage with a file block; the file reaches the client as part of the message."""
    report = {
        "type": "file",
        "base64": base64.b64encode(REPORT.encode()).decode(),
        "mime_type": "text/csv",
        "filename": "units.csv",
    }
    text = {"type": "text", "text": "The report is attached to this message."}
    return {"messages": [AIMessage(content=[text, report])]}
