"""Human-in-the-loop, the ADK way: end the turn, remember, pick up next turn."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from google.adk.events import Event
from google.adk.events.event_actions import EventActions

from src.commands import COMMANDS_BY_KEY
from src.replies import say

ASK = COMMANDS_BY_KEY["ask"]

AWAITING_KEY = "showcase.awaiting_environment"
"""Session-state flag marking that the last turn asked a question."""


def is_awaiting_answer(ctx: AionInvocationContext) -> bool:
    """Return True when the previous turn left a question open."""
    return bool(ctx.session.state.get(AWAITING_KEY))


def _state_event(value: bool) -> Event:
    """Build the event that carries the state change for this turn."""
    return Event(
        author="agent",
        content=None,
        partial=False,
        actions=EventActions(state_delta={AWAITING_KEY: value}),
    )


async def ask_handler(ctx: AionInvocationContext) -> AsyncGenerator[Event, None]:
    """Ask for the missing detail and record that we are waiting for it.

    The turn ends here: an ADK agent answers and returns, it does not park
    mid-run. What carries the conversation to the next turn is session state,
    written through ``EventActions(state_delta=...)`` — everything in that
    delta is visible to the next invocation, and the session is keyed by the
    conversation's context id.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)
    await say(
        thread,
        ASK,
        "Before I continue I need one detail: which environment should I use?",
        "",
        "Reply with anything. This turn is finished — the answer arrives as a "
        "new turn, and session state is what tells me a question is open.",
    )
    yield _state_event(True)


async def answer_handler(ctx: AionInvocationContext, answer: str) -> AsyncGenerator[Event, None]:
    """Consume the answer to the open question and clear the flag."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    await say(
        thread,
        ASK,
        f'Got it — continuing with "{answer.strip() or "no answer given"}".',
        "",
        "The previous turn ended after asking. What matched your answer to "
        "the open question is session state: the flag it wrote was still there "
        "when this turn started, because the session is keyed by the "
        "conversation's context id.",
    )
    yield _state_event(False)
