"""`message`: an answer that is a message, with no task work to track.

The server copies the last message of a finished task into its
``aion:assistant-answer`` artifact.
"""

from __future__ import annotations

import uuid

from a2a.types import Message, Part, Role
from aion.core.a2a import A2AOutbox
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from src.commands.task import inbound_ids
from src.tour import Command, TourState

COMMAND = Command(
    key="message",
    summary="An A2A Message built by the agent and placed in the outbox",
    api="A2AOutbox(message=...)",
    native="an AIMessage returned from a node",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Return an A2A Message you built under ``a2a_outbox``, after a message that explains it."""
    thread = Thread.from_context(runtime.context)
    task_id, context_id = inbound_ids(runtime.context)
    outbound = Message(
        message_id=str(uuid.uuid4()),
        role=Role.ROLE_AGENT,
        parts=[Part(text="An explicit A2A message, built by the agent.")],
        task_id=task_id,
        context_id=context_id,
    )
    reply = await thread.reply("An A2A Message built by the agent is on its way." + COMMAND.footer)
    return {"messages": [reply], "a2a_outbox": A2AOutbox(message=outbound)}


async def with_langgraph(state: TourState) -> dict:
    """Return an AIMessage: that is the answer, and the client gets it as a message."""
    return {"messages": [AIMessage("A plain AIMessage, returned from the node.")]}
