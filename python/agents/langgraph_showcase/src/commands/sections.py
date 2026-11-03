"""`sections`: two streamed sections in one turn, as when a model answers, calls a tool and answers again.

Each section starts the task's ``aion:stream-delta`` artifact over: the client
sees both on the stream, and the task keeps only the last.
"""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from src.tour import Command, TourState, chat_model, stream_text

COMMAND = Command(
    key="sections",
    summary="Two streamed sections in one turn; the task keeps the last",
    api="thread.reply(async iterator), twice",
    native="every chat model call in a turn streams a section of its own",
)

FIRST_SECTION = "Let me check that with a tool."
SECOND_SECTION = "The tool came back, and this second section is the answer."
EXPLAINED = "Two sections were streamed. The task keeps only the second: a new section starts `aion:stream-delta` over."


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Stream two sections with ``thread.reply()``, a thought between them, then explain in a message."""
    thread = Thread.from_context(runtime.context)
    first = await thread.reply(stream_text(FIRST_SECTION))
    await thread.thinking("Calling a tool…")
    second = await thread.reply(stream_text(SECOND_SECTION))
    reply = await thread.reply(EXPLAINED + COMMAND.footer)
    return {"messages": [first, second, reply]}


async def with_langgraph(state: TourState) -> dict:
    """Call a chat model twice in the node: every call streams a section of its own."""
    first = await chat_model(FIRST_SECTION).ainvoke(state["messages"])
    second = await chat_model(SECOND_SECTION).ainvoke(state["messages"])
    return {"messages": [first, second, AIMessage(EXPLAINED)]}
