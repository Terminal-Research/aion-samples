"""`post`: a message with no route of its own, beside a reply that carries the inbound route.

``thread.reply()`` adds the route of the inbound event, so the control plane
delivers it back to where the question came from. ``thread.post()`` adds
none: without a ``target`` the control plane delivers it by the
distribution's Reply Mode.
"""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread

from src.tour import Command

COMMAND = Command(
    key="post",
    summary="A message posted without a route, beside a reply that carries one",
    api="thread.post() / thread.reply()",
    no_native="routes belong to the platform",
)

POSTED = "Posted with `thread.post()`: it has no route, so the control plane delivers it by the distribution's Reply Mode."


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Post one message with ``thread.post()``, then reply with ``thread.reply()``."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.post(POSTED)
    await thread.reply(
        "Replied with `thread.reply()`: it carries the route of your message, so it goes back to where you "
        "asked. A direct A2A call has no route, so here neither message has one." + COMMAND.footer
    )


# No `with_adk`: routes belong to the platform, and `post native` says so.
