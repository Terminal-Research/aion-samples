"""Human-in-the-loop: stop mid-run, ask for input, resume where you stopped."""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from src.replies import with_footer
from src.state import AgentState


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
    """Ask the question, and nothing else.

    The question and the wait deliberately live in two nodes. LangGraph replays
    a node from its first line when the graph resumes, so anything emitted
    before ``interrupt()`` in the same node would be sent twice. Keep side
    effects out of the node that interrupts.
    """
    thread = Thread.from_context(runtime.context)

    reply = await thread.reply(
        with_footer(
            "ask",
            "Before I continue I need one detail: which environment should I use?",
            "",
            "Reply with anything — the task is parked in the input-required state "
            "until you do, and picks up from the same point afterwards.",
        )
    )
    return {"messages": [reply]}


async def ask_wait_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Suspend the run, then acknowledge the answer once it arrives."""
    answer = _resumed_text(interrupt("Waiting for the environment name"))

    thread = Thread.from_context(runtime.context)

    reply = await thread.reply(
        with_footer(
            "ask",
            f'Got it — continuing with "{answer or "no answer given"}".',
            "",
            "The run did not restart: it resumed inside the node that was waiting, "
            "with everything it had already computed still in state.",
        )
    )
    return {"messages": [reply]}
