"""Message-shaped demonstrations: streaming, typing, reactions, metadata."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import data_artifact

from src.replies import with_footer
from src.streaming import TYPEWRITER_DELAY_SECONDS, stream_text


async def stream_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Stream one reply a few words at a time.

    ``thread.reply()`` accepts an async iterator of strings and emits every
    chunk as a partial ADK event, then one durable event with the whole text.
    A model-backed agent passes its own token stream here instead.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    text = with_footer(
        "stream",
        "This sentence reached you in small chunks, the way a model's tokens "
        "arrive — grouped a few words at a time, so a short answer costs a "
        "handful of events instead of one per word. When the stream ends, "
        "the SDK emits the whole message once more so the conversation "
        "history holds a single entry rather than a pile of fragments.",
        "",
        "This is the only command that streams text the agent already had: "
        "every other reply is one `thread.reply(text)` call. The `llm` "
        "command streams too, but those chunks are an `LlmAgent`'s events.",
    )
    await thread.reply(stream_text(text, delay=TYPEWRITER_DELAY_SECONDS))


async def typing_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Emit ephemeral indicators, then a durable reply.

    Ephemeral events reach the client but are never persisted in task history.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.typing("Looking that up…")
    await thread.typing("Almost there…")

    await thread.reply(
        with_footer(
            "typing",
            "You just saw two typing indicators. They were delivered to you but "
            "not persisted: ask for `context` afterwards and the message count "
            "will not have counted them.",
        )
    )


async def react_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Add a reaction to the inbound message, then remove it.

    Reactions target a provider message, so they need an inbound event carrying
    a context id and a message id — that is, delivery through a distribution.
    Over a direct A2A call there is no provider message to react to.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    if thread.message is None or ctx.aion_runtime_context.event is None:
        await thread.reply(
            with_footer(
                "react",
                "This turn did not arrive through a distribution, so there is no "
                "provider message to react to. Send `react` from a connected "
                "channel and a thumbs-up will appear on your message and then "
                "disappear.",
            )
        )
        return

    await thread.message.react("thumbsup", display_value=":thumbsup:")
    await thread.message.react("thumbsup", operation="remove")

    await thread.reply(
        with_footer(
            "react",
            "A thumbs-up was added to your message and then removed again. Both "
            "operations go out as reaction actions for the distribution to apply.",
        )
    )


async def metadata_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Attach custom metadata to a message and to an artifact.

    Keys beginning with ``aion:`` are reserved for the platform; anything else
    travels untouched and comes back on the event you receive.
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
        with_footer(
            "metadata",
            "Two events went out with custom metadata: one message and one data "
            "artifact. Inspect them in the raw A2A stream — metadata is preserved "
            "verbatim, except for keys under the reserved `aion:` prefix.",
        )
    )
