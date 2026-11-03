"""Human-in-the-loop: stop mid-run, ask for input, resume where you stopped."""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from src.replies import with_footer
from src.state import AgentState

QUESTION = "Which environment should I use?"
"""The question `ask` waits on, as the task's input-required status shows it."""


def _resumed_text(value: object) -> str:
    """Extract the user's answer from whatever the resume payload carries.

    The server resumes the graph with ``{"messages": [HumanMessage(...)]}``, and
    the message content arrives as content blocks rather than a plain string —
    the same shape the inbound message has on any other turn.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        messages = value.get("messages") or []
        if messages:
            last = messages[-1]
            content = last.content if isinstance(last, BaseMessage) else last
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                return "".join(
                    block.get("text", "") for block in content if isinstance(block, dict)
                ).strip()
    return ""


async def ask_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Say what is about to happen, and nothing else.

    The explanation is a message, and it stays in the conversation history.
    The question itself is not sent here: it is the value of ``interrupt()``
    in the next node, which the server makes the message of the task's
    input-required status.

    The explanation and the wait deliberately live in two nodes. LangGraph
    replays a node from its first line when the graph resumes, so anything
    emitted before ``interrupt()`` in the same node would be sent twice. Keep
    side effects out of the node that interrupts.
    """
    thread = Thread.from_context(runtime.context)

    reply = await thread.reply(
        with_footer(
            "ask",
            "I need one detail before I continue, so the task is about to wait in "
            "the input-required state, with the question as its status message. "
            "Reply with anything — the run picks up from the same point afterwards.",
        )
    )
    return {"messages": [reply]}


async def ask_wait_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Suspend the run on the question, then answer once the input arrives.

    The interrupt value is the question the client sees on the task's
    input-required status. The text sent after the resume is the task's
    answer, so it goes out as a text artifact.
    """
    answer = _resumed_text(interrupt(QUESTION))

    thread = Thread.from_context(runtime.context)

    await thread.reply(
        text_artifact(
            with_footer(
                "ask",
                f'Got it — continuing with "{answer or "no answer given"}".',
                "",
                "The run did not restart: it resumed inside the node that was waiting, "
                "with everything it had already computed still in state.",
            )
        )
    )
    return {}
