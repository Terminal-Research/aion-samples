"""An ADK agent with nothing Aion-specific in it.

Nothing here imports from ``aion``. The SDK puts the inbound message into the
ADK session as a user event and hands it to the agent as ``ctx.user_content``.
The agent answers the way ADK keeps any output of a run: it saves the answer
through the invocation's artifact service (``CallbackContext.save_artifact``)
and yields the event that records the saved version. The SDK sends that
version to the client as an artifact of the task, which makes it the task's
result.
"""

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from typing_extensions import override

ANSWER_FILENAME = "answer"
"""Artifact the agent saves its answer under. Each turn saves the next version of it."""


class PlainAgent(BaseAgent):
    """Describes the latest user message and counts the turns so far."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        parts = ctx.user_content.parts if ctx.user_content and ctx.user_content.parts else []
        text = "".join(part.text or "" for part in parts).strip()
        turns = sum(1 for event in ctx.session.events if event.author == "user")
        answer = (
            f'You said {len(text.split())} word(s): "{text}". '
            f"That was message {turns} in this conversation."
        )

        # save_artifact stores the part and notes its version in `actions`;
        # the event carries that note and no content, so the answer is not
        # also a text event of the agent.
        actions = EventActions()
        await CallbackContext(ctx, event_actions=actions).save_artifact(
            ANSWER_FILENAME, types.Part(text=answer)
        )
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=actions)


def create_agent() -> PlainAgent:
    """Build the agent; the Aion server runs it."""
    return PlainAgent(
        name="plain",
        description="An ADK agent with nothing Aion-specific in it",
    )
