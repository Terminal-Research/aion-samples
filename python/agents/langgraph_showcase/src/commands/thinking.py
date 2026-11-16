"""`thinking`: the agent's thoughts, shown to the client beside the answer, not in it.

Thoughts go to the task's ``aion:thinking-delta`` artifact. They are not
messages, so the conversation does not keep them.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="thinking",
    summary="The agent's thoughts, kept beside the history rather than in it",
    api="thread.thinking()",
    no_native="a model's reasoning does not reach the client",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send each thought with ``thread.thinking()``, then the answer."""
    thread = Thread.from_context(runtime.context)
    await thread.thinking("Looking that up…")
    await thread.thinking("Almost there…")
    await thread.reply(text_artifact("Two thoughts came before this answer." + COMMAND.footer))
    return {}


# No `with_langgraph`: LangGraph alone cannot show thoughts, and `thinking native` says so.
