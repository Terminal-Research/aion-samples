"""`context`: what the agent knows about this turn, the conversation and the caller.

A turn can come over a direct A2A call or through a distribution such as
Slack; ``Thread.from_context()`` gives both the same fields. LangGraph alone
knows the thread the run belongs to.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="context",
    summary="What the agent knows about this conversation and its caller",
    api="Thread.from_context() / context.event",
    native="config['configurable']['thread_id']",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Read the turn from ``Thread.from_context()`` and ``runtime.context``."""
    thread = Thread.from_context(runtime.context)
    event = runtime.context.event
    distribution = runtime.context.get_distribution()
    principal = runtime.context.get_principal_identity()
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
            f"  messages in state  {len(state.get('messages') or [])}",
        ]
    )
    await thread.reply(text_artifact(report + COMMAND.footer))
    return {}


async def with_langgraph(state: TourState, config: RunnableConfig) -> dict:
    """Read the thread id from the run's config: it joins the agent, the caller and the context id."""
    report = "\n".join(
        [
            "This turn:",
            f"  thread id          {config['configurable']['thread_id']}",
            f"  messages in state  {len(state.get('messages') or [])}",
        ]
    )
    return {"messages": [AIMessage(report)]}


def _show(value: object) -> str:
    """A value for display, with a dash for an absent one."""
    return str(value) if value not in (None, "") else "—"
