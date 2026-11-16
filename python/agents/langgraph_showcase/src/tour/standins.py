"""Stand-ins for a model, so the tour runs without one."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

WORDS_PER_CHUNK = 10
"""Words per chunk of ``stream_text``: a short reply is a handful of events, not one per word."""

TYPEWRITER_DELAY_SECONDS = 0.05
"""Pause between chunks of ``stream_text``, so the text visibly arrives in pieces."""


async def stream_text(text: str) -> AsyncIterator[str]:
    """Yield ``text`` a few words at a time, the way a model streams its tokens."""
    words = text.split(" ")
    for start in range(0, len(words), WORDS_PER_CHUNK):
        chunk = " ".join(words[start:start + WORDS_PER_CHUNK])
        yield chunk if start == 0 else f" {chunk}"
        await asyncio.sleep(TYPEWRITER_DELAY_SECONDS)


def chat_model(answer: str) -> GenericFakeChatModel:
    """A LangChain chat model that answers ``answer``, streaming it word by word.

    Any LangChain chat model streams the same way when a node calls it.
    """
    return GenericFakeChatModel(messages=iter([AIMessage(content=answer)]))
