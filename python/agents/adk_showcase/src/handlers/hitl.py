"""Human-in-the-loop, the ADK way: end the turn, remember, pick up next turn."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from google.adk.events import Event
from google.adk.events.event_actions import EventActions

from src.replies import with_footer

AWAITING_KEY = "showcase.awaiting_environment"
"""Session-state flag marking that the last turn asked a question."""

QUESTION = "Before I continue I need one detail: which environment should I use?"
"""The question `ask` leaves open for the next turn."""


def is_awaiting_answer(ctx: AionInvocationContext) -> bool:
    """Return True when the previous turn left a question open."""
    return bool(ctx.session.state.get(AWAITING_KEY))


async def ask_handler(ctx: AionInvocationContext, argument: str) -> AsyncGenerator[Event, None]:
    """Ask for the missing detail and record that we are waiting for it.

    The turn ends here: an ADK agent answers and returns, it does not park
    mid-run. What carries the conversation to the next turn is session state,
    written through ``EventActions(state_delta=...)`` — everything in that
    delta is visible to the next invocation, and the session is keyed by the
    conversation's context id.

    The question is a message: it is what the agent says while it waits for
    input, not a result. The explanation of the demonstration is the task's
    result, a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(QUESTION)
    await thread.reply(
        text_artifact(
            with_footer(
                "ask",
                "Reply with anything. This turn is finished — the answer arrives as a "
                "new turn, and session state is what tells me a question is open.",
            )
        )
    )

    # AWAITING_KEY is this sample's own key; the delta is what the next
    # invocation of this session will see.
    yield Event(
        author="agent",
        content=None,
        partial=False,
        actions=EventActions(state_delta={AWAITING_KEY: True}),
    )


async def answer_handler(ctx: AionInvocationContext, answer: str) -> AsyncGenerator[Event, None]:
    """Consume the answer to the open question and clear the flag.

    What the agent does with the answer is the task's result, a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        text_artifact(
            with_footer(
                "ask",
                f'Got it — continuing with "{answer.strip() or "no answer given"}".',
                "",
                "The previous turn ended after asking. What matched your answer to "
                "the open question is session state: the flag it wrote was still there "
                "when this turn started, because the session is keyed by the "
                "conversation's context id.",
            )
        )
    )

    yield Event(
        author="agent",
        content=None,
        partial=False,
        actions=EventActions(state_delta={AWAITING_KEY: False}),
    )
