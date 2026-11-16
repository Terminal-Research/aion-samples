"""`data`: a structured result, which another agent can read without parsing prose.

A data part is a protobuf ``Value``, so every number in it arrives as a float.
"""

from __future__ import annotations

import json

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import data_artifact

from src.tour import Command

COMMAND = Command(
    key="data",
    summary="A structured data artifact",
    api="data_artifact()",
    no_native="an ADK part carries no structured data",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Send the data as an artifact with ``thread.reply()``, then explain it in a message."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    payload = {"status": "ok", "totals": {"north": 120, "south": 98}, "generated_by": "adk_showcase"}
    await thread.reply(data_artifact(payload, name="totals"))
    await thread.reply(
        "That artifact holds data, not text:\n"
        + json.dumps(payload, indent=2)
        + "\n\nA data part is a protobuf `Value`, so every number arrives as a float: `120` is `120.0`."
        + COMMAND.footer
    )


# No `with_adk`: an ADK part carries no structured data, and `data native` says so.
