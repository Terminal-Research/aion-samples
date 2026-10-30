"""Message-shaped demonstrations: streaming, thinking, reactions, metadata."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import data_artifact, text_artifact

from src.replies import with_footer
from src.streaming import TYPEWRITER_DELAY_SECONDS, stream_text


async def stream_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Stream one answer a few words at a time.

    ``thread.reply()`` accepts an async iterator of strings and emits every
    chunk as a partial ADK event, a section of the task's ``aion:stream-delta``
    artifact, then one complete event that ends the section without sending
    the text again. The streamed text, footer included, is the task's result;
    the ADK session keeps the complete event as what the agent said. A
    model-backed agent passes its own token stream here instead.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

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
        "every other answer is one `thread.reply(text_artifact(text))` call. "
        "The `llm` command streams too, but those chunks are an `LlmAgent`'s "
        "events.",
    )
    await thread.reply(stream_text(text, delay=TYPEWRITER_DELAY_SECONDS))


async def thinking_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Share two thoughts, then answer.

    A thought goes to the task's ``aion:thinking-delta`` artifact, one text
    part per thought. It is not a message, so neither the conversation
    history nor the ADK session holds it. The answer that follows is the
    task's result, a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.thinking("Looking that up…")
    await thread.thinking("Almost there…")

    await thread.reply(
        text_artifact(
            with_footer(
                "thinking",
                "You just saw two thoughts. They are kept in the task's "
                "`aion:thinking-delta` artifact, not as messages: ask for `context` "
                "afterwards and the event count will not have counted them.",
            )
        )
    )


async def react_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Add a reaction to the inbound message, then remove it.

    Reactions target a provider message, so they need an inbound event carrying
    a context id and a message id — that is, delivery through a distribution.
    Over a direct A2A call there is no provider message to react to. Either
    way the explanation is the task's result, a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    if thread.message is None or ctx.aion_runtime_context.event is None:
        await thread.reply(
            text_artifact(
                with_footer(
                    "react",
                    "This turn did not arrive through a distribution, so there is no "
                    "provider message to react to. Send `react` from a connected "
                    "channel and a thumbs-up will appear on your message and then "
                    "disappear.",
                )
            )
        )
        return

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


async def metadata_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Attach custom metadata to a message and to an artifact.

    Keys beginning with ``aion:`` are reserved for the platform; anything else
    travels untouched and comes back on the event you receive. The message is
    what this command demonstrates, so it stays a message; the explanation
    after it is the task's result, a text artifact.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        "This message carries metadata.",
        metadata={"showcase.step": "message", "showcase.run": "demo"},
    )
    await thread.reply(
        data_artifact({"checked": True}, name="metadata_demo"),
        metadata={"showcase.step": "artifact"},
    )

    await thread.reply(
        text_artifact(
            with_footer(
                "metadata",
                "Two events went out with custom metadata: one message and one data "
                "artifact. Inspect them in the raw A2A stream — metadata is preserved "
                "verbatim, except for keys under the reserved `aion:` prefix.",
            )
        )
    )
