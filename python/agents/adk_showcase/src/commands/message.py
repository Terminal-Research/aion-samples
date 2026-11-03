"""`message`: an answer that is a message, with no task work to track.

The server copies the last message of a finished task into its
``aion:assistant-answer`` artifact.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from a2a.types import Message, Part, Role
from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import A2AOutbox
from google.adk.events import Event, EventActions
from google.genai import types

from src.commands.task import inbound_ids
from src.tour import Command

COMMAND = Command(
    key="message",
    summary="An A2A Message built by the agent and placed in the outbox",
    api="A2AOutbox(message=...)",
    native="a text event of the agent",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Put an A2A Message you built in ``a2a_outbox``, after a message that explains it."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    task_id, context_id = inbound_ids(ctx.aion_runtime_context)
    outbound = Message(
        message_id=str(uuid.uuid4()),
        role=Role.ROLE_AGENT,
        parts=[Part(text="An explicit A2A message, built by the agent.")],
        task_id=task_id,
        context_id=context_id,
    )
    await thread.reply("An A2A Message built by the agent is on its way." + COMMAND.footer)
    yield Event(author="agent", actions=EventActions(state_delta={"a2a_outbox": A2AOutbox(message=outbound)}))


async def with_adk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Yield a text event: that is the answer, and the client gets it as a message."""
    yield Event(
        invocation_id=ctx.invocation_id,
        author=ctx.agent.name,
        content=types.Content(role="model", parts=[types.Part(text="A plain text event of the agent.")]),
    )
