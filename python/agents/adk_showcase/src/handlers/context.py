"""What the agent knows about the conversation it is in."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread

from src.replies import with_footer


def _show(value: object) -> str:
    """Render a context value for display, marking absent ones explicitly."""
    return str(value) if value not in (None, "") else "—"


async def context_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Report the identity and coordinates of the current turn.

    The same agent can be reached directly over A2A or through a distribution
    such as Slack. ``Thread.from_context()`` normalizes both into the same
    fields, so agent code does not branch on the provider.
    """
    runtime = ctx.aion_runtime_context
    thread = Thread.from_context(runtime)

    event = runtime.event
    distribution = runtime.get_distribution()
    principal = runtime.get_principal_identity()
    history_length = len(ctx.session.events or [])

    await thread.reply(
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
