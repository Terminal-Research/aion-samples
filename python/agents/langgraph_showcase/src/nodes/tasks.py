"""Task-shaped demonstrations: progress, explicit A2A responses, failure."""

from __future__ import annotations

import asyncio
import uuid

from a2a.types import Artifact, Message as A2AMessage, Part, Role, Task, TaskState, TaskStatus
from aion.core.a2a import A2AOutbox
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.commands import COMMANDS_BY_KEY
from src.replies import say
from src.state import AgentState

PROGRESS = COMMANDS_BY_KEY["progress"]
TASK = COMMANDS_BY_KEY["task"]
MESSAGE = COMMANDS_BY_KEY["message"]
FAIL = COMMANDS_BY_KEY["fail"]

STEPS = ("Fetching input", "Crunching numbers", "Writing the result")


def _inbound_ids(runtime: Runtime[AionRuntimeContext]) -> tuple[str, str]:
    """Return the inbound task and context ids, or fresh ones for a direct call."""
    inbox = runtime.context.inbox
    if inbox is not None and inbox.task is not None:
        return inbox.task.id, inbox.task.context_id
    if inbox is not None and inbox.message is not None:
        message = inbox.message
        return message.task_id or str(uuid.uuid4()), message.context_id or str(uuid.uuid4())
    return str(uuid.uuid4()), str(uuid.uuid4())


async def progress_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Report progress while the work is still running.

    Each step goes out as an ephemeral update, so the caller sees movement
    without the history filling up with status lines. This is also the shape to
    watch when you want to observe cancellation: cancel the task from the
    client while the steps are still arriving.
    """
    thread = Thread.from_context(runtime.context)

    for index, step in enumerate(STEPS, start=1):
        await thread.typing(f"[{index}/{len(STEPS)}] {step}…")
        await asyncio.sleep(1.0)

    return await say(
        thread,
        PROGRESS,
        f"Finished all {len(STEPS)} steps.",
        "",
        "To see cancellation, send `progress` again and cancel the task while "
        "the steps are still coming in.",
    )


async def task_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Answer with an explicit A2A Task instead of letting the SDK build one.

    Everything above this uses the thread helpers and lets the server assemble
    the response. When you need full control — your own history, artifacts and
    metadata on the task — put a Task in the outbox.
    """
    thread = Thread.from_context(runtime.context)
    task_id, context_id = _inbound_ids(runtime)

    task = Task(
        id=task_id,
        context_id=context_id,
        status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
        history=[
            A2AMessage(
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

    update = await say(
        thread,
        TASK,
        "An explicit A2A Task is on its way out, carrying its own history, one "
        "artifact and custom metadata.",
    )
    return {**update, "a2a_outbox": A2AOutbox(task=task)}


async def message_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Answer with a bare A2A Message.

    A Message is the right response when there is no work to track — no task
    lifecycle, just a reply bound to the same context.
    """
    thread = Thread.from_context(runtime.context)
    task_id, context_id = _inbound_ids(runtime)

    outbound = A2AMessage(
        message_id=str(uuid.uuid4()),
        role=Role.ROLE_AGENT,
        parts=[Part(text="An explicit A2A message, built by the agent.")],
        task_id=task_id,
        context_id=context_id,
    )

    update = await say(
        thread,
        MESSAGE,
        "An explicit A2A Message is on its way out — same context, no task "
        "lifecycle attached.",
    )
    return {**update, "a2a_outbox": A2AOutbox(message=outbound)}


async def fail_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Finish the task in the failed state, on purpose.

    Failure is part of the contract: the caller needs a terminal state it can
    act on, not a silent stop. Returning a failed Task says what went wrong and
    ends the task cleanly.
    """
    thread = Thread.from_context(runtime.context)
    task_id, context_id = _inbound_ids(runtime)

    failed = Task(
        id=task_id,
        context_id=context_id,
        status=TaskStatus(state=TaskState.TASK_STATE_FAILED),
        history=[
            A2AMessage(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_AGENT,
                parts=[Part(text="Deliberate failure raised by the showcase agent.")],
            )
        ],
        metadata={"reason": "demonstration"},
    )

    update = await say(
        thread,
        FAIL,
        "This task is ending in the failed state on purpose. The client should "
        "see a terminal failure, not a hang and not a success.",
    )
    return {**update, "a2a_outbox": A2AOutbox(task=failed)}
