"""Message-shaped demonstrations: streaming, thinking, reactions, metadata."""

from __future__ import annotations

from aion.core.a2a import data_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.replies import with_footer
from src.state import AgentState
from src.streaming import TYPEWRITER_DELAY_SECONDS, stream_text


async def stream_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Stream one reply a few words at a time.

    ``thread.reply()`` accepts an async iterator and emits every chunk as it
    arrives, as a section of the task's ``aion:stream-delta`` artifact. The
    streamed text is the task's answer, not a message, and is not sent again
    when the stream ends. A model-backed agent passes its own token stream
    here instead.
    """
    thread = Thread.from_context(runtime.context)

    text = with_footer(
        "stream",
        "This sentence reached you in small chunks, the way a model's tokens "
        "arrive — grouped a few words at a time, so a short answer costs a "
        "handful of events instead of one per word. The chunks are the "
        "task's `aion:stream-delta` artifact, not messages: when the task "
        "finishes, the server joins them into one text, so the task holds "
        "the answer once rather than a pile of fragments.",
        "",
        "This is the only command that streams text the agent already had: "
        "every other reply is one `thread.reply(text)` call. The `llm` "
        "command streams too, but those chunks are the model's own.",
    )
    reply = await thread.reply(stream_text(text, delay=TYPEWRITER_DELAY_SECONDS))
    return {"messages": [reply]}


async def thinking_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Share two thoughts, then reply.

    A thought goes to the task's ``aion:thinking-delta`` artifact, one text
    part per thought. It is not a message, so neither the conversation
    history nor the graph's state holds it.
    """
    thread = Thread.from_context(runtime.context)

    await thread.thinking("Looking that up…")
    await thread.thinking("Almost there…")

    reply = await thread.reply(
        with_footer(
            "thinking",
            "You just saw two thoughts. They are kept in the task's "
            "`aion:thinking-delta` artifact, not as messages: ask for `context` "
            "afterwards and the message count will not have counted them.",
        )
    )
    return {"messages": [reply]}


async def react_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Add a reaction to the inbound message, then remove it.

    Reactions target a provider message, so they need an inbound event carrying
    a context id and a message id — that is, delivery through a distribution.
    Over a direct A2A call there is no provider message to react to.
    """
    thread = Thread.from_context(runtime.context)

    if thread.message is None or runtime.context.event is None:
        reply = await thread.reply(
            with_footer(
                "react",
                "This turn did not arrive through a distribution, so there is no "
                "provider message to react to. Send `react` from a connected "
                "channel and a thumbs-up will appear on your message and then "
                "disappear.",
            )
        )
        return {"messages": [reply]}

    await thread.message.react("thumbsup", display_value=":thumbsup:")
    await thread.message.react("thumbsup", operation="remove")

    reply = await thread.reply(
        with_footer(
            "react",
            "A thumbs-up was added to your message and then removed again. Both "
            "operations go out as reaction actions for the distribution to apply.",
        )
    )
    return {"messages": [reply]}


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

    reply = await thread.reply(
        with_footer(
            "metadata",
            "Two events went out with custom metadata: one message and one data "
            "artifact. Inspect them in the raw A2A stream — metadata is preserved "
            "verbatim, except for keys under the reserved `aion:` prefix.",
        )
    )
    return {"messages": [reply]}
