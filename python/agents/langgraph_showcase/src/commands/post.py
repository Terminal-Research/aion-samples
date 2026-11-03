"""`post`: a message with no route of its own, beside a reply that carries the inbound route.

``thread.reply()`` adds the route of the inbound event, so the control plane
delivers it back to where the question came from. ``thread.post()`` adds
none: without a ``target`` the control plane delivers it by the
distribution's Reply Mode.
"""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="post",
    summary="A message posted without a route, beside a reply that carries one",
    api="thread.post() / thread.reply()",
    no_native="routes belong to the platform",
)

POSTED = "Posted with `thread.post()`: it has no route, so the control plane delivers it by the distribution's Reply Mode."


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Post one message with ``thread.post()``, then reply with ``thread.reply()``."""
    thread = Thread.from_context(runtime.context)
    posted = await thread.post(POSTED)
    reply = await thread.reply(
        "Replied with `thread.reply()`: it carries the route of your message, so it goes back to where you "
        "asked. A direct A2A call has no route, so here neither message has one." + COMMAND.footer
    )
    return {"messages": [posted, reply]}


# No `with_langgraph`: routes belong to the platform, and `post native` says so.
