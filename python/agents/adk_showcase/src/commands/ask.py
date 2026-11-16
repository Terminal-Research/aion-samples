"""`ask`: the agent stops to ask for missing input, then resumes where it stopped.

The pause is ADK's own: a long-running function call, so ``ask native`` runs
this command as it is. The task waits in the input-required state with the
question as its status message, and the user's reply comes back as the call's
function response.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Optional

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from google.adk.events import Event
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="ask",
    summary="The agent asks for missing input, then resumes where it stopped",
    api="Event(long_running_tool_ids=...)",
    native="a long-running function call, which `ask` already makes",
)

REQUEST_INPUT = "adk_request_input"
"""The function ADK's own ``request_input`` tool calls to ask the user."""

QUESTION = "Which environment should I use?"
"""The question `ask` waits on, as the task's input-required status shows it."""


async def with_sdk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Say that a question is coming, then pause the run on a long-running function call.

    The call is the one ADK's ``request_input`` tool makes. The task waits in
    the input-required state with the question as its status message, and the
    user's reply comes back as the call's function response.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        "I need one detail first, so the task will wait in the input-required state "
        "with the question as its status message. Reply with anything to continue." + COMMAND.footer
    )

    call_id = f"adk-{uuid.uuid4()}"
    yield Event(
        author=ctx.agent.name,
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        id=call_id, name=REQUEST_INPUT, args={"message": QUESTION}
                    )
                )
            ],
        ),
        long_running_tool_ids={call_id},
    )


def answered_question(ctx: AionInvocationContext) -> Optional[str]:
    """Return the user's answer when this turn resumes `ask`, or None for any other turn.

    The resumed run gets the reply as its user content: the function
    response to the call it paused on. A plain-text reply arrives as
    ``{"result": text}``, a JSON object as that object.
    """
    parts = (ctx.user_content.parts if ctx.user_content is not None else None) or []
    for part in parts:
        response = part.function_response
        if response is not None and response.name == REQUEST_INPUT:
            value = response.response or {}
            return str(value["result"]) if "result" in value else json.dumps(value)
    return None


async def answer(ctx: AionInvocationContext, reply: str) -> None:
    """Answer with what the user replied to the question; the turn that resumes `ask` runs this."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await thread.reply(
        text_artifact(
            f'Got it — continuing with "{reply.strip() or "no answer given"}". '
            "The run resumed in the invocation that asked." + COMMAND.footer
        )
    )
