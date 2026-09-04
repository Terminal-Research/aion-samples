"""Message-shaped demonstrations: streaming, typing, reactions, metadata."""

from __future__ import annotations

from aion.core.a2a import data_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.commands import COMMANDS_BY_KEY
from src.replies import say
from src.state import AgentState
from src.streaming import TYPEWRITER_DELAY_SECONDS

STREAM = COMMANDS_BY_KEY["stream"]
TYPING = COMMANDS_BY_KEY["typing"]
REACT = COMMANDS_BY_KEY["react"]
METADATA = COMMANDS_BY_KEY["metadata"]


async def stream_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Stream one reply a few words at a time.

    ``thread.reply()`` accepts an async iterator and emits every chunk as it
    arrives, then posts the accumulated message once as durable history. A
    model-backed agent passes its own token stream here instead.
    """
    thread = Thread.from_context(runtime.context)
    return await say(
        thread,
        STREAM,
        "This sentence reached you in small chunks, the way a model's tokens "
        "arrive — grouped a few words at a time, so a short answer costs a "
        "handful of events instead of one per word. When the stream ends, "
        "the SDK posts the whole message once more so the conversation "
        "history holds a single entry rather than a pile of fragments.",
        "",
        "This is the only command that paces itself. Everywhere else the "
        "chunks go out back to back, because a deliberate pause is time "
        "you would spend waiting for nothing.",
        delay=TYPEWRITER_DELAY_SECONDS,
    )


async def typing_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Emit ephemeral indicators, then a durable reply.

    Ephemeral messages reach the client but are filtered out by the task store,
    so they never appear in the conversation history.
    """
    thread = Thread.from_context(runtime.context)

    await thread.typing("Looking that up…")
    await thread.typing("Almost there…")

    return await say(
        thread,
        TYPING,
        "You just saw two typing indicators. They were delivered to you but "
        "not persisted: ask for `context` afterwards and the message count "
        "will not have counted them.",
    )


async def react_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Add a reaction to the inbound message, then remove it.

    Reactions target a provider message, so they need an inbound event carrying
    a context id and a message id — that is, delivery through a distribution.
    Over a direct A2A call there is no provider message to react to.
    """
    thread = Thread.from_context(runtime.context)

    if thread.message is None or runtime.context.event is None:
        return await say(
            thread,
            REACT,
            "This turn did not arrive through a distribution, so there is no "
            "provider message to react to. Send `react` from a connected "
            "channel and a thumbs-up will appear on your message and then "
            "disappear.",
        )

    await thread.message.react("thumbsup", display_value=":thumbsup:")
    await thread.message.react("thumbsup", operation="remove")

    return await say(
        thread,
        REACT,
        "A thumbs-up was added to your message and then removed again. Both "
        "operations go out as reaction actions for the distribution to apply.",
    )


async def metadata_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Attach custom metadata to a message and to an artifact.

    Keys beginning with ``aion:`` are reserved for the platform; anything else
    travels untouched and comes back on the event you receive.
    """
    thread = Thread.from_context(runtime.context)

    await thread.reply(
        "This message carries metadata.",
        metadata={"showcase.step": "message", "showcase.run": "demo"},
    )
    await thread.reply(
        data_artifact({"checked": True}, name="metadata_demo"),
        metadata={"showcase.step": "artifact"},
    )

    return await say(
        thread,
        METADATA,
        "Two events went out with custom metadata: one message and one data "
        "artifact. Inspect them in the raw A2A stream — metadata is preserved "
        "verbatim, except for keys under the reserved `aion:` prefix.",
    )
