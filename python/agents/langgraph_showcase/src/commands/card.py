"""`card`: rich cards, one composed from components and one referenced by URL.

A card is a message. A button with an ``id`` comes back as a card-action
event: "Try ask" has the id ``ask``, so pressing it runs `ask`. A button with
a ``url`` only opens the link.
"""

from __future__ import annotations

from aion.core.agent.invocation.card import Actions, Button, Card, Divider, Field, Fields, Text
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="card",
    summary="Rich cards, composed from components and referenced by URL",
    api="Card / Text / Fields / Actions",
    no_native="cards belong to the platform",
)

# A card document hosted elsewhere; the client fetches and renders it.
REMOTE_CARD_URL = "https://docs.aion.to/a2a/extensions/aion/distribution/cards/1.0.0"


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Explain what follows, then send a composed card and a card referenced by URL."""
    thread = Thread.from_context(runtime.context)
    reply = await thread.reply(
        "Two cards follow: one composed from components, one hosted elsewhere. "
        'Press "Try ask" to send a card action.' + COMMAND.footer
    )
    await thread.reply(
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
    await thread.reply(Card(url=REMOTE_CARD_URL))
    return {"messages": [reply]}


# No `with_langgraph`: cards belong to the platform, and `card native` says so.
