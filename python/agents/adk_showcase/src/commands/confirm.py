"""`confirm`: the agent asks to confirm an action, then decides itself what the answer means.

The pause is ADK's confirmation: a long-running ``adk_request_confirmation``
call, the one ``tool_context.request_confirmation`` makes, so ``confirm native``
runs this command as it is. The question comes with a card of two buttons, and
the user's reply comes back as the call's function response, an ADK
``ToolConfirmation``:

- ``{"confirmed": true}`` - the client sent ADK's own object;
- ``{"payload": {"data": {..., "actionId": "approve"}}}`` - a button was pressed;
- ``{"payload": {"text": "sure"}}`` - the answer was typed.

The SDK reads no button and no word as a yes: whatever is not ADK's object
reaches the agent unconfirmed, and the agent decides (``agreed``). A tool of an
``LlmAgent`` that asks with ``tool_context.request_confirmation`` reads the same
payload in ``tool_context.tool_confirmation``, or judges it in the agent's
``before_tool_callback``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from aion.core.agent.invocation.card import Actions, Button, Card, Text
from google.adk.events import Event
from google.genai import types

from src.tour import Command

COMMAND = Command(
    key="confirm",
    summary="The agent asks to confirm an action, and decides itself what the answer means",
    api="adk_request_confirmation + ToolConfirmation.payload",
    native="a long-running confirmation call, which `confirm` already makes",
)

REQUEST_CONFIRMATION = "adk_request_confirmation"
"""The function ADK calls when a tool asks the user to confirm it."""

QUESTION = "Delete the build cache?"
"""What `confirm` asks, as the task's input-required status shows it."""

APPROVE = "approve"
REJECT = "reject"
"""The action ids of the two buttons; a pressed button comes back with its id."""

YES = frozenset({"yes", "y", "ok", "sure", "go ahead"})
"""What this agent takes a typed answer to mean yes. It is the agent's choice, not the SDK's."""


async def with_sdk(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Show the question with two buttons, then pause the run on a confirmation call."""
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        "I need your confirmation first, so the task will wait in the input-required state. "
        "Press a button, or type your answer." + COMMAND.footer
    )
    await thread.reply(
        Card("Confirmation")
        .add(Text(QUESTION))
        .add(
            Actions()
            .add(Button("Yes", id=APPROVE, style="primary"))
            .add(Button("No", id=REJECT, style="danger"))
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
                        id=call_id,
                        name=REQUEST_CONFIRMATION,
                        args={"toolConfirmation": {"hint": QUESTION, "confirmed": False}},
                    )
                )
            ],
        ),
        long_running_tool_ids={call_id},
    )


def answered_confirmation(ctx: AionInvocationContext) -> Optional[dict[str, Any]]:
    """Return the confirmation when this turn resumes `confirm`, or None for any other turn."""
    parts = (ctx.user_content.parts if ctx.user_content is not None else None) or []
    for part in parts:
        response = part.function_response
        if response is not None and response.name == REQUEST_CONFIRMATION:
            return response.response or {}
    return None


def agreed(confirmation: dict[str, Any]) -> bool:
    """What this agent takes the answer to mean: ADK's object as it says, else its own reading."""
    if "confirmed" in confirmation:
        return bool(confirmation["confirmed"])
    answer = confirmation.get("payload") or {}
    pressed = (answer.get("data") or {}).get("actionId")
    if pressed:
        return pressed == APPROVE
    return str(answer.get("text", "")).strip().lower() in YES


def _how(confirmation: dict[str, Any]) -> str:
    """How the user answered, in the words of the reply."""
    if "confirmed" in confirmation:
        return "You sent ADK's confirmation object."
    answer = confirmation.get("payload") or {}
    pressed = (answer.get("data") or {}).get("actionId")
    if pressed:
        return f'You pressed the button "{pressed}".'
    return f'You typed "{answer.get("text", "")}".'


async def answer(ctx: AionInvocationContext, confirmation: dict[str, Any]) -> None:
    """Say what the agent made of the answer; the turn that resumes `confirm` runs this."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    verdict = (
        "Confirmed: the build cache would be deleted now."
        if agreed(confirmation)
        else "Not confirmed: the build cache stays."
    )
    await thread.reply(text_artifact(f"{_how(confirmation)} {verdict}" + COMMAND.footer))
