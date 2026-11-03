"""What the agent knows about the conversation it is in, and what it was sent."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src.replies import with_footer


def _show(value: object) -> str:
    """Render a context value for display, marking absent ones explicitly."""
    return str(value) if value not in (None, "") else "—"


async def context_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Report the identity and coordinates of the current turn.

    The same agent can be reached directly over A2A or through a distribution
    such as Slack. ``Thread.from_context()`` normalizes both into the same
    fields, so agent code does not branch on the provider. The report is the
    task's result, a text artifact.
    """
    runtime = ctx.aion_runtime_context
    thread = Thread.from_context(runtime)

    event = runtime.event
    distribution = runtime.get_distribution()
    principal = runtime.get_principal_identity()
    history_length = len(ctx.session.events or [])

    await thread.reply(
        text_artifact(
            with_footer(
                "context",
                "This turn:",
                f"  network            {_show(thread.network)}",
                f"  context id         {_show(thread.context_id)}",
                f"  parent context id  {_show(thread.parent_context_id)}",
                f"  event kind         {_show(event.kind if event else None)}",
                f"  distribution       {_show(distribution.endpoint_type if distribution else None)}",
                f"  principal          {_show(principal.id if principal else None)}",
                f"  sender             {_show(thread.message.user.id if thread.message and thread.message.user else None)}",
                f"  session            {_show(ctx.session.id)}",
                f"  events in session  {history_length}",
                "",
                "Send `context` again in the same conversation: the event count grows, "
                "because turns sharing a context id share an ADK session.",
            )
        )
    )


def _describe(part) -> str:
    """One line for a file part: its name, its media type and what it holds."""
    if part.WhichOneof("content") == "raw":
        held = f"{len(part.raw)} bytes inline"
    else:
        held = f"a link, {part.url}"
    return f"  {part.filename or '(no name)'}  {part.media_type or 'no media type'}, {held}"


async def attachment_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Describe the files attached to the inbound message.

    Every part of the inbound message reaches the agent in
    ``aion_runtime_context.inbox.message``, the A2A message as the server
    received it; the invocation's ``user_content`` holds the same files as
    ``inline_data`` and ``file_data`` parts for a model. A file is a part
    holding inline bytes (``raw``) or a link (``url``), with its name and
    media type beside it. With a file storage backend configured, the server
    stores inline bytes before the agent runs, so the agent sees a link;
    without one the bytes arrive as they were sent. The description is the
    task's result, a text artifact; a turn without a file says so in a
    message.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    inbox = ctx.aion_runtime_context.inbox
    message = ctx.aion_runtime_context.inbox.message if inbox is not None else None
    files = [
        part for part in (message.parts if message is not None else [])
        if part.WhichOneof("content") in ("raw", "url")
    ]

    if not files:
        await thread.reply(
            with_footer(
                "attachment",
                "Attach a file to `attachment` and I will describe it: a file reaches "
                "the agent as a part of your message, inline bytes or a link.",
            )
        )
        return

    await thread.reply(
        text_artifact(
            with_footer(
                "attachment",
                f"Your message carried {len(files)} file(s):",
                *[_describe(part) for part in files],
                "",
                "With a file storage backend configured, the server stores inline "
                "bytes before the agent runs, so the agent sees a link instead; "
                "without one the bytes arrive as they were sent.",
            )
        )
    )
