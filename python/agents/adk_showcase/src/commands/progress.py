"""`progress`: long-running work that reports each step before it finishes.

Each step is a thought, so the client sees movement without the conversation
filling up. Cancel the task while the steps arrive to see cancellation.
"""

from __future__ import annotations

import asyncio

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src.tour import Command

COMMAND = Command(
    key="progress",
    summary="Long-running work reporting its steps before it finishes",
    api="thread.thinking() during work",
    no_native="ADK has no progress of its own that reaches the client",
)

STEPS = ("Fetching input", "Crunching numbers", "Writing the result")
STEP_SECONDS = 1.0


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Report each step with ``thread.thinking()`` while the work runs, then answer."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    for index, step in enumerate(STEPS, start=1):
        await thread.thinking(f"[{index}/{len(STEPS)}] {step}…")
        await asyncio.sleep(STEP_SECONDS)
    await thread.reply(text_artifact(f"Finished all {len(STEPS)} steps." + COMMAND.footer))


# No `with_adk`: ADK has no progress of its own that reaches the client, and `progress native` says so.
