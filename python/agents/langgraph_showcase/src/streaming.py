"""Text streaming without a language model.

One command streams: `stream` hands ``thread.reply()`` an async iterator built
here, so the reply arrives in pieces the way a model's tokens do. Every other
reply is a single string, because chunking text the agent already holds buys
nothing but events.

The other streaming reply in this agent is `llm`, and it does not come through
here: those chunks are the model's own.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

WORDS_PER_CHUNK = 10
"""Words per streamed chunk. Large enough that a short reply is a handful of
events rather than one per word, small enough that the text still visibly
arrives in pieces."""

TYPEWRITER_DELAY_SECONDS = 0.05
"""Pause between chunks. The pacing is the point of the demonstration; a real
agent lets the model set the pace instead."""


async def stream_text(text: str, *, delay: float) -> AsyncIterator[str]:
    """Yield text in small groups of words, the way a model streams tokens.

    Args:
        text: Full text to stream.
        delay: Pause between chunks, in seconds.

    Yields:
        Chunks of the original text, whitespace preserved at chunk boundaries.
    """
    words = text.split(" ")
    for start in range(0, len(words), WORDS_PER_CHUNK):
        chunk = " ".join(words[start:start + WORDS_PER_CHUNK])
        yield chunk if start == 0 else f" {chunk}"
        await asyncio.sleep(delay)
