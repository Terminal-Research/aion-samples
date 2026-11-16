"""`attachment`: the files the user attached, as the agent receives them.

A file arrives as a part of the user's message: inline bytes (``raw``) or a
link (``url``), with its name and media type. With file storage configured,
the server stores inline bytes before the agent runs, so the agent sees a link.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="attachment",
    summary="The files you attach, as the agent receives them",
    api="context.inbox.message",
    native="the file blocks of the HumanMessage in state",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """List the file parts of ``runtime.context.inbox.message``, the A2A message the server received."""
    thread = Thread.from_context(runtime.context)
    message = runtime.context.inbox.message if runtime.context.inbox is not None else None
    files = [part for part in (message.parts if message else []) if part.WhichOneof("content") in ("raw", "url")]
    if not files:
        await thread.reply(text_artifact("Attach a file to `attachment` and I will describe it." + COMMAND.footer))
        return {}

    lines = [f"Your message carried {len(files)} file(s):"] + [_describe(part) for part in files]
    await thread.reply(text_artifact("\n".join(lines) + COMMAND.footer))
    return {}


async def with_langgraph(state: TourState) -> dict:
    """List the file blocks of the user's last message in ``state["messages"]``."""
    content = [message for message in state["messages"] if isinstance(message, HumanMessage)][-1].content
    blocks = [block for block in content if isinstance(block, dict) and block.get("type") != "text"] if isinstance(content, list) else []
    if not blocks:
        return {"messages": [AIMessage("Attach a file to `attachment native` and I will describe it.")]}

    lines = [f"Your message carried {len(blocks)} file(s):"] + [
        f"  {block.get('filename') or '(no name)'}  {block.get('mime_type') or 'no media type'}, a {block['type']} block"
        for block in blocks
    ]
    return {"messages": [AIMessage("\n".join(lines))]}


def _describe(part) -> str:
    """One line for a file part: its name, its media type and what it holds."""
    held = f"{len(part.raw)} bytes inline" if part.WhichOneof("content") == "raw" else f"a link, {part.url}"
    return f"  {part.filename or '(no name)'}  {part.media_type or 'no media type'}, {held}"
