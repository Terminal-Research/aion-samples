"""`attachment`: the files the user attached, as the agent receives them.

A file arrives as a part of the user's message: inline bytes (``raw``) or a
link (``url``), with its name and media type. With file storage configured,
the server stores inline bytes before the agent runs, so the agent sees a link.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from google.adk.events import Event
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="attachment",
    summary="The files you attach, as the agent receives them",
    api="aion_runtime_context.inbox.message",
    native="the inline_data and file_data parts of ctx.user_content",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """List the file parts of ``ctx.aion_runtime_context.inbox.message``, the A2A message the server received."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    inbox = ctx.aion_runtime_context.inbox
    message = ctx.aion_runtime_context.inbox.message if inbox is not None else None
    files = [part for part in (message.parts if message else []) if part.WhichOneof("content") in ("raw", "url")]
    if not files:
        await thread.reply("Attach a file to `attachment` and I will describe it." + COMMAND.footer)
        return

    lines = [f"Your message carried {len(files)} file(s):"] + [_describe(part) for part in files]
    await thread.reply(text_artifact("\n".join(lines) + COMMAND.footer))


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """List the ``inline_data`` and ``file_data`` parts of ``ctx.user_content``."""
    parts = ctx.user_content.parts if ctx.user_content and ctx.user_content.parts else []
    lines = [
        f"  {part.inline_data.display_name or '(no name)'}  {part.inline_data.mime_type}, {len(part.inline_data.data)} bytes inline"
        for part in parts if part.inline_data
    ] + [
        f"  {part.file_data.display_name or '(no name)'}  {part.file_data.mime_type}, a link, {part.file_data.file_uri}"
        for part in parts if part.file_data
    ]
    text = (
        "\n".join([f"Your message carried {len(lines)} file(s):", *lines])
        if lines else "Attach a file to `attachment native` and I will describe it."
    )
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _describe(part) -> str:
    """One line for a file part: its name, its media type and what it holds."""
    held = f"{len(part.raw)} bytes inline" if part.WhichOneof("content") == "raw" else f"a link, {part.url}"
    return f"  {part.filename or '(no name)'}  {part.media_type or 'no media type'}, {held}"
