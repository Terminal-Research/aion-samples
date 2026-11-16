"""`task`: an A2A Task the agent builds itself, with its own history, artifacts and metadata.

A Task in the outbox replaces the one the server would assemble from the turn.
"""

from __future__ import annotations

import uuid

from a2a.types import Artifact, Message, Part, Role, Task, TaskState, TaskStatus
from aion.core.a2a import A2AOutbox
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="task",
    summary="An A2A Task built by the agent and placed in the outbox",
    api="A2AOutbox(task=...)",
    no_native="an A2A Task belongs to the platform",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Return the Task under ``a2a_outbox``, after a message that explains it."""
    thread = Thread.from_context(runtime.context)
    task_id, context_id = inbound_ids(runtime.context)
    task = Task(
        id=task_id,
        context_id=context_id,
        status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
        history=[
            Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_AGENT,
                parts=[Part(text="First message of the explicit task history.")],
            )
        ],
        artifacts=[
            Artifact(
                artifact_id=str(uuid.uuid4()),
                name="explicit_artifact",
                parts=[Part(text="Attached by the agent, not by the SDK.")],
            )
        ],
        metadata={"built_by": "showcase"},
    )
    reply = await thread.reply(
        "An A2A Task built by the agent is on its way, with its own history, artifact and metadata."
        + COMMAND.footer
    )
    return {"messages": [reply], "a2a_outbox": A2AOutbox(task=task)}


def inbound_ids(context: AionRuntimeContext) -> tuple[str, str]:
    """The task and context ids of the inbound turn, or fresh ones for a call that carries none."""
    inbox = context.inbox
    if inbox is not None and inbox.task is not None:
        return inbox.task.id, inbox.task.context_id
    if inbox is not None and inbox.message is not None:
        return inbox.message.task_id or str(uuid.uuid4()), inbox.message.context_id or str(uuid.uuid4())
    return str(uuid.uuid4()), str(uuid.uuid4())


# No `with_langgraph`: an A2A Task belongs to the platform, and `task native` says so.
