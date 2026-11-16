"""`stream`: an answer that reaches the client in chunks while it is written.

The chunks are the task's ``aion:stream-delta`` artifact; when the task
finishes, the server joins them into one text.
"""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState, chat_model, stream_text

COMMAND = Command(
    key="stream",
    summary="An answer streamed in chunks as it is written",
    api="thread.reply(async iterator)",
    native="a chat model called in a node streams by itself",
)

ANSWER = "This answer reached you in chunks, the way a model's tokens arrive."


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Hand ``thread.reply()`` any async iterator of text; every item goes out as a chunk."""
    thread = Thread.from_context(runtime.context)
    reply = await thread.reply(stream_text(ANSWER + COMMAND.footer))
    return {"messages": [reply]}  # the graph's state keeps the conversation


async def with_langgraph(state: TourState) -> dict:
    """Return the answer of a chat model called in the node; LangGraph streams its tokens by itself."""
    answer = await chat_model(ANSWER).ainvoke(state["messages"])
    return {"messages": [answer]}
