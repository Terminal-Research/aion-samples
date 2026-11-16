"""`react`: a reaction put on the user's message, then taken back.

A reaction targets the provider message a distribution delivered, so it needs
a turn that came through one, such as Slack.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="react",
    summary="A reaction added to, then removed from, your message",
    api="message.react()",
    no_native="reactions belong to the platform",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """React with ``thread.message.react()``, or say why there is nothing to react to."""
    thread = Thread.from_context(runtime.context)
    if thread.message is None or runtime.context.event is None:
        await thread.reply(
            text_artifact(
                "A direct A2A call has no provider message to react to. Send `react` from a connected channel."
                + COMMAND.footer
            )
        )
        return {}

    await thread.message.react("thumbsup", display_value=":thumbsup:")
    await thread.message.react("thumbsup", operation="remove")
    await thread.reply(text_artifact("A thumbs-up was added to your message and removed again." + COMMAND.footer))
    return {}


# No `with_langgraph`: reactions belong to the platform, and `react native` says so.
