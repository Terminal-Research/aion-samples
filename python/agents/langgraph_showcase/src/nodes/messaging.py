"""Message-shaped demonstrations: streaming, thinking, reactions, metadata."""

from __future__ import annotations

from aion.core.a2a import data_artifact, text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.replies import with_footer
from src.state import AgentState
from src.streaming import TYPEWRITER_DELAY_SECONDS, stream_text


async def stream_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Stream one answer a few words at a time.

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
        "every other answer that is text is one `thread.reply(text_artifact(text))` call. "
        "The `llm` command streams too, but those chunks are the model's own.",
    )
    reply = await thread.reply(stream_text(text, delay=TYPEWRITER_DELAY_SECONDS))
    return {"messages": [reply]}


FIRST_SECTION = "Let me check that for you. One moment while I look it up with a tool."
"""What `sections` streams before its step."""

SECOND_SECTION = (
    "The tool came back. This second section is the answer, streamed after the "
    "step that came between."
)
"""What `sections` streams after its step."""


async def sections_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Stream two sections in one turn, with a step between them.

    A model that answers, calls a tool and answers again streams twice. Each
    ``thread.reply()`` with an async iterator is one section of the task's
    ``aion:stream-delta`` artifact, and a new section starts that artifact
    over: the client sees both sections on the stream, and the task keeps only
    the last. Text that has to outlive the next section goes out as a message
    or an artifact of its own. Both streamed sections are kept in state, as
    `stream` keeps its answer; the explanation after them is a message.
    """
    thread = Thread.from_context(runtime.context)

    first = await thread.reply(stream_text(FIRST_SECTION, delay=TYPEWRITER_DELAY_SECONDS))
    await thread.thinking("Calling a tool…")
    second = await thread.reply(stream_text(SECOND_SECTION, delay=TYPEWRITER_DELAY_SECONDS))

    reply = await thread.reply(
        with_footer(
            "sections",
            "Two sections were streamed in this turn, with a thought between them. "
            "The stream showed you both; the task keeps only the second, because a "
            "new section starts the `aion:stream-delta` artifact over. Fetch the task "
            "again and the first section is gone.",
        )
    )
    return {"messages": [first, second, reply]}


async def thinking_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Share two thoughts, then answer.

    A thought goes to the task's ``aion:thinking-delta`` artifact, one text
    part per thought. It is not a message, so neither the conversation
    history nor the graph's state holds it.
    """
    thread = Thread.from_context(runtime.context)

    await thread.thinking("Looking that up…")
    await thread.thinking("Almost there…")

    await thread.reply(
        text_artifact(
            with_footer(
                "thinking",
                "You just saw two thoughts. They are kept in the task's "
                "`aion:thinking-delta` artifact, not as messages: ask for `context` "
                "afterwards and the message count will not have counted them.",
            )
        )
    )
    return {}


async def react_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Add a reaction to the inbound message, then remove it.

    Reactions target a provider message, so they need an inbound event carrying
    a context id and a message id — that is, delivery through a distribution.
    Over a direct A2A call there is no provider message to react to, so
    the turn only says so, in a message: nothing was done.
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

    await thread.reply(
        text_artifact(
            with_footer(
                "react",
                "A thumbs-up was added to your message and then removed again. Both "
                "operations go out as reaction actions for the distribution to apply.",
            )
        )
    )
    return {}


POSTED = "This message was sent with `thread.post()` and carries no route."
"""The message `post` posts."""


async def post_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Post a message without a route, then explain it in a reply that has one.

    ``thread.reply()`` adds the route of the inbound event to whatever it
    sends, and the control plane delivers it back to where the question came
    from. ``thread.post()`` adds none of its own: without a ``target`` its
    message carries no route, and the control plane delivers it by the
    distribution's Reply Mode; ``target=MessageActionPayload(...)`` sends it
    somewhere specific. Over a direct A2A call there is no channel, so
    neither message carries a route. Both texts are messages.
    """
    thread = Thread.from_context(runtime.context)

    posted = await thread.post(POSTED)

    if runtime.context.event is None:
        situation = (
            "This turn came over a direct A2A call, so neither message carries a "
            "route: there is no channel to route to. Send `post` from a connected "
            "channel to see the difference."
        )
    else:
        situation = (
            "This reply carries the route of your message, so it goes back to where "
            "you asked; the message above goes by the distribution's Reply Mode."
        )

    reply = await thread.reply(
        with_footer(
            "post",
            "`thread.reply()` adds the route of the inbound event — where the "
            "question came from — to everything it sends. `thread.post()` adds none "
            "of its own: without a `target` the control plane delivers its message "
            "by the distribution's Reply Mode, and `target=MessageActionPayload(...)` "
            "sends it somewhere specific.",
            "",
            situation,
        )
    )
    return {"messages": [posted, reply]}


async def metadata_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Attach custom metadata to a message and to an artifact.

    Keys beginning with ``aion:`` are reserved for the platform; anything else
    travels untouched and comes back on the event you receive. The data
    artifact is the task's result; the message that carries metadata and the
    explanation after both are messages.
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
