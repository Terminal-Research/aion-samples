"""Card demonstrations: composed from components, and referenced by URL."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.agent.invocation.card import Actions, Button, Card, Divider, Field, Fields, Text

from src.replies import with_footer

# A card document hosted elsewhere; the client fetches and renders it.
REMOTE_CARD_URL = "https://docs.aion.to/a2a/extensions/aion/distribution/cards/1.0.0"


async def card_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Send a composed card and a card referenced by URL.

    Cards render natively where the channel supports them and degrade to text
    where it does not, so an agent can send one without knowing the surface.
    Buttons with an ``id`` come back as card-action events; buttons with a
    ``url`` just open a link.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    composed = (
        Card("Deployment ready")
        .add(Text("Build 128 passed every check and is waiting for approval."))
        .add(
            Fields()
            .add(Field("Environment", "production"))
            .add(Field("Build", "#128"))
            .add(Field("Duration", "4m 12s"))
        )
        .add(Divider())
        .add(
            Actions()
            .add(Button("Try ask", id="ask", style="primary"))
            .add(Button("Cards extension", url=REMOTE_CARD_URL))
        )
    )
    await thread.reply(composed)
    await thread.reply(Card(url=REMOTE_CARD_URL))

    await thread.reply(
        with_footer(
            "card",
            "Two cards: the first was composed from typed components, the second "
            "points at a card document hosted elsewhere. This is the only "
            "command that sends cards — every other reply is plain text, so a "
            "channel that renders no cards still gets the whole tour.",
            "",
            'The "Try ask" button carries an action id. Pressing it sends a '
            "card-action event, which this agent routes to the same handler as "
            "typing `ask` — see src/agent.py.",
        )
    )
