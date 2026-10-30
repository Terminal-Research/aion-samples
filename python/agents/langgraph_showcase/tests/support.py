"""What a node hands to ``thread.reply()``, captured instead of sent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from a2a.types import Artifact
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage


@dataclass(frozen=True)
class Reply:
    """One ``thread.reply()`` call: what was sent, and the metadata given with it."""

    content: Any
    metadata: dict | None


def capture_replies(monkeypatch) -> list[Reply]:
    """Replace ``Thread.reply`` with a fake that records every call.

    The node calls ``thread.reply()`` itself, so the fake stands in for the SDK
    and returns what the real call returns: the posted message for text and
    for a stream, None for a card or an artifact.
    """
    captured: list[Reply] = []

    async def fake_reply(self, content, *, metadata=None):
        captured.append(Reply(content, metadata))
        if isinstance(content, str):
            return AIMessage(content=content)
        if hasattr(content, "__aiter__"):
            return AIMessage(content="".join([chunk async for chunk in content]))
        return None

    monkeypatch.setattr(Thread, "reply", fake_reply)
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
