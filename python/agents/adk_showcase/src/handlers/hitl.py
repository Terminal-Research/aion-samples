"""Human-in-the-loop, the ADK way: pause on a long-running call, resume with its answer."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Optional

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from google.adk.events import Event
from google.genai import types

from src.replies import with_footer

REQUEST_INPUT = "adk_request_input"
"""The function ADK's own ``request_input`` tool calls to ask the user."""

QUESTION = "Which environment should I use?"
"""The question `ask` waits on, as the task's input-required status shows it."""


async def ask_handler(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Say what is about to happen, then pause the run on the question.

    An ADK run pauses on a long-running function call: the agent makes the
    call, marks it in ``long_running_tool_ids`` and returns, and the answer
    arrives later as the call's function response. The call here is the one
    ADK's ``request_input`` tool makes, ``adk_request_input`` with the
    question as its ``message``. The server keeps the task waiting in the
    input-required state with the question as its status message, and turns
    the user's reply into the function response the call waits for. The
    explanation sent before the call is a message.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        with_footer(
            "ask",
            "I need one detail before I continue, so the task is about to wait in "
            "the input-required state, with the question as its status message. "
            "Reply with anything — the run picks up from the same call afterwards.",
        )
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


async def answer_handler(ctx: AionInvocationContext, answer: str) -> None:
    """Continue from the question with the answer it waited for.

    What the agent does with the answer is the task's result, a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        text_artifact(
            with_footer(
                "ask",
                f'Got it — continuing with "{answer.strip() or "no answer given"}".',
                "",
                "The run did not start over: it resumed in the invocation that asked, "
                "and ADK handed your reply to the call it paused on as that call's "
                "function response.",
            )
        )
    )
