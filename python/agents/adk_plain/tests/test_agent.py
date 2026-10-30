"""The agent, run directly with ADK's in-memory services — no server, no SDK."""

import asyncio

from google.adk.agents.invocation_context import InvocationContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agent import ANSWER_FILENAME, create_agent

APP = "plain"
USER = "user-1"


def _content(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _run(text: str, earlier_user_turns: int = 0) -> tuple[list[Event], InvocationContext]:
    """Run one turn against a session that already holds the current user event."""

    async def run() -> tuple[list[Event], InvocationContext]:
        agent = create_agent()
        sessions = InMemorySessionService()
        session = await sessions.create_session(app_name=APP, user_id=USER)
        for turn in [*(["earlier"] * earlier_user_turns), text]:
            await sessions.append_event(session, Event(author="user", content=_content(turn)))
        ctx = InvocationContext(
            invocation_id="invocation-1",
            agent=agent,
            session=session,
            session_service=sessions,
            artifact_service=InMemoryArtifactService(),
            user_content=_content(text),
        )
        return [event async for event in agent._run_async_impl(ctx)], ctx

    return asyncio.run(run())


def _answer(events: list[Event], ctx: InvocationContext) -> str:
    """Return the text of the artifact version the only event records."""
    [event] = events
    version = event.actions.artifact_delta[ANSWER_FILENAME]

    async def load() -> types.Part:
        return await ctx.artifact_service.load_artifact(
            app_name=ctx.app_name,
            user_id=ctx.user_id,
            session_id=ctx.session.id,
            filename=ANSWER_FILENAME,
            version=version,
        )

    return asyncio.run(load()).text


def test_agent_is_named_after_its_aion_yaml_entry():
    """The agent id in aion.yaml and the agent name match."""
    assert create_agent().name == "plain"


def test_answer_is_an_artifact_not_a_text_event():
    """The one event the agent yields records a saved artifact and carries no content."""
    events, _ = _run("hello world")
    assert len(events) == 1
    assert events[0].content is None
    assert events[0].partial is not True
    assert list(events[0].actions.artifact_delta) == [ANSWER_FILENAME]


def test_answer_describes_the_message():
    """The answer quotes the message and counts its words."""
    assert 'You said 2 word(s): "hello world"' in _answer(*_run("hello world"))


def test_answer_counts_the_turns():
    """The turn number follows the user events in the session."""
    assert "message 3 in this conversation" in _answer(*_run("third", earlier_user_turns=2))
