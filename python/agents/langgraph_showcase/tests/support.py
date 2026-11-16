"""What a node hands to the thread, captured instead of sent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from a2a.types import Artifact
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage


@dataclass(frozen=True)
class Reply:
    """One ``thread.reply()`` or ``thread.post()`` call: what was sent, and how.

    Attributes:
        content: What the node sent.
        metadata: The metadata given with it.
        via: ``reply`` or ``post``, the call that sent it.
        target: The target given to ``post``; a reply never names one.
    """

    content: Any
    metadata: dict | None
    via: str = "reply"
    target: Any = None


async def _sent(content):
    """What the real call returns: the posted message for text and a stream, None otherwise."""
    if isinstance(content, str):
        return AIMessage(content=content)
    if hasattr(content, "__aiter__"):
        return AIMessage(content="".join([chunk async for chunk in content]))
    return None


def capture_replies(monkeypatch) -> list[Reply]:
    """Replace ``Thread.reply`` and ``Thread.post`` with fakes that record every call.

    The node calls the thread itself, so the fakes stand in for the SDK and
    return what the real calls return.
    """
    captured: list[Reply] = []

    async def fake_reply(self, content, *, metadata=None):
        captured.append(Reply(content, metadata))
        return await _sent(content)

    async def fake_post(self, content, *, target=None, metadata=None):
        captured.append(Reply(content, metadata, via="post", target=target))
        return await _sent(content)

    monkeypatch.setattr(Thread, "reply", fake_reply)
    monkeypatch.setattr(Thread, "post", fake_post)
    return captured


def capture_thoughts(monkeypatch) -> list[str]:
    """Replace ``Thread.thinking`` with a fake that records every thought."""
    captured: list[str] = []

    async def fake_thinking(self, text, *args, **kwargs):
        captured.append(text)

    monkeypatch.setattr(Thread, "thinking", fake_thinking)
    return captured


def message_text(reply: Reply) -> str:
    """Return the text of a message, failing unless the reply was plain text."""
    assert isinstance(reply.content, str), f"expected a message, got {type(reply.content).__name__}"
    return reply.content


def answer_text(reply: Reply) -> str:
    """Return the text of an answer, failing unless it is a one-part text artifact."""
    artifact = reply.content
    assert isinstance(artifact, Artifact), f"expected a text artifact, got {type(artifact).__name__}"
    assert len(artifact.parts) == 1 and artifact.parts[0].HasField("text"), artifact
    return artifact.parts[0].text
