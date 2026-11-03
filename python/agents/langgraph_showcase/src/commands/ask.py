"""`ask`: the agent stops to ask for missing input, then resumes where it stopped.

The pause is LangGraph's own ``interrupt()``, so ``ask native`` runs this
command as it is. The task waits in the input-required state with the
question as its status message, and the user's reply resumes the run.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from src.tour import Command, TourState

COMMAND = Command(
    key="ask",
    summary="The agent asks for missing input, then resumes where it stopped",
    api="interrupt()",
    native="interrupt(), which `ask` already uses",
)

QUESTION = "Which environment should I use?"


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Say that a question is coming; the next node, ``wait``, asks it.

    LangGraph replays a node from its first line when the graph resumes, so
    whatever a node sends before ``interrupt()`` would go out twice.
    """
    thread = Thread.from_context(runtime.context)
    reply = await thread.reply(
        "I need one detail first, so the task will wait in the input-required state "
        "with the question as its status message. Reply with anything to continue." + COMMAND.footer
    )
    return {"messages": [reply]}


async def wait(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Wait on the question with ``interrupt()``, then answer with what the user replied."""
    answer = _resumed_text(interrupt(QUESTION))
    thread = Thread.from_context(runtime.context)
    await thread.reply(
        text_artifact(
            f'Got it — continuing with "{answer or "no answer given"}". '
            "The run resumed inside the node that was waiting." + COMMAND.footer
        )
    )
    return {}


def _resumed_text(value: object) -> str:
    """The user's answer from the resume value: ``{"messages": [HumanMessage(...)]}``, or text."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict) and value.get("messages"):
        last = value["messages"][-1]
        content = last.content if isinstance(last, BaseMessage) else last
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "".join(block.get("text", "") for block in content if isinstance(block, dict)).strip()
    return ""
