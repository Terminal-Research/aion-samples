"""`data`: a structured result, which another agent can read without parsing prose.

A data part is a protobuf ``Value``, so every number in it arrives as a float.
"""

from __future__ import annotations

import json

from aion.core.a2a import data_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="data",
    summary="A structured data artifact",
    api="data_artifact()",
    no_native="LangGraph has no data parts",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send the data as an artifact with ``thread.reply()``, then explain it in a message."""
    thread = Thread.from_context(runtime.context)
    payload = {"status": "ok", "totals": {"north": 120, "south": 98}, "generated_by": "langgraph_showcase"}
    await thread.reply(data_artifact(payload, name="totals"))
    reply = await thread.reply(
        "That artifact holds data, not text:\n"
        + json.dumps(payload, indent=2)
        + "\n\nA data part is a protobuf `Value`, so every number arrives as a float: `120` is `120.0`."
        + COMMAND.footer
    )
    return {"messages": [reply]}


# No `with_langgraph`: LangGraph has no data parts, and `data native` says so.
