"""`react`: a reaction put on the user's message, then taken back.

A reaction targets the provider message a distribution delivered, so it needs
a turn that came through one, such as Slack.
"""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src.tour import Command

COMMAND = Command(
    key="react",
    summary="A reaction added to, then removed from, your message",
    api="message.react()",
    no_native="reactions belong to the platform",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """React with ``thread.message.react()``, or say why there is nothing to react to."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    if thread.message is None or ctx.aion_runtime_context.event is None:
        await thread.reply(
            text_artifact(
                "A direct A2A call has no provider message to react to. Send `react` from a connected channel."
                + COMMAND.footer
            )
        )
        return

    await thread.message.react("thumbsup", display_value=":thumbsup:")
    await thread.message.react("thumbsup", operation="remove")
    await thread.reply(text_artifact("A thumbs-up was added to your message and removed again." + COMMAND.footer))


# No `with_adk`: reactions belong to the platform, and `react native` says so.
