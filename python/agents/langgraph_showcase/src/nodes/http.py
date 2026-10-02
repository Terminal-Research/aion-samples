"""The agent's own HTTP surface, alongside A2A."""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.replies import with_footer
from src.state import AgentState


async def http_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Explain the custom routes this agent registers.

    An agent is an HTTP service as well as an A2A endpoint. Routers registered
    with ``app_registry.add_router()`` are mounted next to the built-in
    endpoints, which is where webhooks and health probes belong.
    """
    thread = Thread.from_context(runtime.context)

    reply = await thread.reply(
        with_footer(
            "http",
            "Besides the A2A endpoint, this agent serves:",
            "  GET /showcase/commands          registered in src/api.py",
            "  GET /.well-known/agent-card.json  agent card, built from aion.yaml",
            "  GET /.well-known/configuration.json",
            "  GET /health/",
            "",
            "Through the proxy the same routes live under "
            "/agents/showcase/… — see docs.aion.to for the routing rules.",
        )
    )
    return {"messages": [reply]}
