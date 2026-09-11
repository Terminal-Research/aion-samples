"""An ADK agent with nothing Aion-specific in it.

Nothing here imports from ``aion``. The SDK puts the inbound message into the
ADK session as a user event, hands it to the agent as ``ctx.user_content``,
and turns the ``Event`` the agent yields into the reply.
"""

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from typing_extensions import override


class PlainAgent(BaseAgent):
    """Describes the latest user message and counts the turns so far."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        parts = ctx.user_content.parts if ctx.user_content and ctx.user_content.parts else []
        text = "".join(part.text or "" for part in parts).strip()
        turns = sum(1 for event in ctx.session.events if event.author == "user")
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f'You said {len(text.split())} word(s): "{text}". '
                        f"That was message {turns} in this conversation."
                    )
                ],
            ),
            partial=False,
        )


def create_agent() -> PlainAgent:
    """Build the agent; the Aion server runs it."""
    return PlainAgent(
        name="plain",
        description="An ADK agent with nothing Aion-specific in it",
    )
