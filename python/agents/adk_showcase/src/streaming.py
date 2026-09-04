"""Text streaming without a language model.

The showcase agent has no model behind it: every reply is text the agent already
knows. Streaming it a few words at a time reproduces what a model-backed agent
puts on the wire, so the platform behaviour on display is the real one — without
turning a short answer into a hundred separate events.

Chunks go out as fast as the runtime accepts them. Pacing is opt-in: only the
`stream` demonstration slows itself down, because there the typing effect is the
thing being shown.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

WORDS_PER_CHUNK = 10
"""Words per streamed chunk. Large enough that a short reply is a handful of
events rather than one per word, small enough that the text still visibly
arrives in pieces."""

NO_DELAY = 0.0
"""Default: no artificial pacing, so a reply costs only the events it needs."""

TYPEWRITER_DELAY_SECONDS = 0.05
"""Pause between chunks for the one command that demonstrates the typing
effect. Anywhere else this is time the user waits for nothing."""


async def stream_text(
    text: str,
    *,
    words_per_chunk: int = WORDS_PER_CHUNK,
    delay: float = NO_DELAY,
) -> AsyncIterator[str]:
    """Yield text in small groups of words, the way a model streams tokens.

    Args:
        text: Full text to stream.
        words_per_chunk: Number of words carried by each chunk.
        delay: Pause between chunks, in seconds. Zero — the default — still
            yields to the event loop between chunks, so each one is handed to
            the transport before the next is built.

    Yields:
        Chunks of the original text, whitespace preserved at chunk boundaries.
    """
    words = text.split(" ")
    for start in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[start:start + words_per_chunk])
        yield chunk if start == 0 else f" {chunk}"
        await asyncio.sleep(delay)
