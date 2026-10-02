"""The agent, run directly — no server, no SDK."""

import asyncio
from types import SimpleNamespace

from google.adk.events import Event
from google.genai import types

from src.agent import create_agent


def _content(text: str, role: str = "user") -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def _run(text: str, earlier_user_turns: int = 0) -> str:
    """Run one turn against a session that already holds the current user event."""
    events = [Event(author="user", content=_content("earlier")) for _ in range(earlier_user_turns)]
    events.append(Event(author="user", content=_content(text)))
    ctx = SimpleNamespace(user_content=_content(text), session=SimpleNamespace(events=events))

    async def collect() -> list[Event]:
        return [event async for event in create_agent()._run_async_impl(ctx)]

    replies = asyncio.run(collect())
    assert len(replies) == 1 and replies[0].partial is False
    return replies[0].content.parts[0].text


def test_agent_is_named_after_its_aion_yaml_entry():
    """The agent id in aion.yaml and the agent name match."""
    assert create_agent().name == "plain"


def test_reply_describes_the_message():
    """The reply quotes the message and counts its words."""
    assert 'You said 2 word(s): "hello world"' in _run("hello world")


def test_reply_counts_the_turns():
    """The turn number follows the user events in the session."""
    assert "message 3 in this conversation" in _run("third", earlier_user_turns=2)
