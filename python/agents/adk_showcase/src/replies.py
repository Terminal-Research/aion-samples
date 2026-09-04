"""Shared reply helpers for command handlers."""

from __future__ import annotations

from aion.adk.authoring.invocation import Thread

from src.commands import Command
from src.streaming import NO_DELAY, stream_text


async def say(thread: Thread, command: Command, *lines: str, delay: float = NO_DELAY) -> None:
    """Stream a reply and close it with the command's source footer.

    The footer is what turns the agent into a browsable index of the platform:
    every answer states which SDK call produced it and where that call lives.

    Args:
        thread: Thread bound to the current invocation.
        command: Command being demonstrated.
        *lines: Body lines of the reply.
        delay: Pause between streamed chunks. Defaults to none, so a reply
            arrives as fast as the transport carries it; the `stream` command
            passes a real pause because the pacing is what it demonstrates.
    """
    body = "\n".join([*lines, "", command.footer()])
    await thread.reply(stream_text(body, delay=delay))
