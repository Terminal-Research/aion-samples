"""`fail`: the task fails on purpose, with a reason the caller reads.

``TaskFailedError(reason)`` ends the turn, and the reason becomes the message
of the FAILED status: the same on the stream, in the unary answer and in a
later ``tasks/get``. Any other exception fails the task too, but the caller
reads only that the agent stopped on an unexpected error.
"""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.exceptions import TaskFailedError

from src.tour import Command

COMMAND = Command(
    key="fail",
    summary="The task fails on purpose, with a reason the caller reads",
    api="TaskFailedError(reason)",
    native="any exception raised in the agent, which the caller sees only as an unexpected error",
)

REASON = "Deliberate failure raised by the showcase agent."


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Explain in a message, then raise ``TaskFailedError`` with the reason."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply("This task is failing on purpose. Its FAILED status will carry the reason." + COMMAND.footer)
    raise TaskFailedError(REASON)


async def with_adk(ctx: AionInvocationContext, argument: str) -> None:
    """Raise any exception; its text stays in the agent's log."""
    raise RuntimeError("Deliberate failure raised by the showcase agent, without the SDK.")
