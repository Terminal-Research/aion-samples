"""`context`: what the agent knows about this turn, the conversation and the caller.

A turn can come over a direct A2A call or through a distribution such as
Slack; ``Thread.from_context()`` gives both the same fields. ADK alone knows
the session the run belongs to and its user.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from google.adk.events import Event
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="context",
    summary="What the agent knows about this conversation and its caller",
    api="Thread.from_context() / context.event",
    native="ctx.session.id and ctx.user_id",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Read the turn from ``Thread.from_context()`` and ``ctx.aion_runtime_context``."""
    runtime = ctx.aion_runtime_context
    thread = Thread.from_context(runtime)
    event = runtime.event
    distribution = runtime.get_distribution()
    principal = runtime.get_principal_identity()
    sender = thread.message.user.id if thread.message and thread.message.user else None
    report = "\n".join(
        [
            "This turn:",
            f"  network            {_show(thread.network)}",
            f"  context id         {_show(thread.context_id)}",
            f"  parent context id  {_show(thread.parent_context_id)}",
            f"  event kind         {_show(event.kind if event else None)}",
            f"  distribution       {_show(distribution.endpoint_type if distribution else None)}",
            f"  principal          {_show(principal.id if principal else None)}",
            f"  sender             {_show(sender)}",
            f"  events in session  {len(ctx.session.events or [])}",
        ]
    )
    await thread.reply(text_artifact(report + COMMAND.footer))


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Read the session and the user from the invocation context."""
    report = "\n".join(
        [
            "This turn:",
            f"  session            {ctx.session.id}",
            f"  user               {ctx.user_id}",
            f"  events in session  {len(ctx.session.events or [])}",
        ]
    )
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text=report)]),
    )


def _show(value: object) -> str:
    """A value for display, with a dash for an absent one."""
    return str(value) if value not in (None, "") else "—"
