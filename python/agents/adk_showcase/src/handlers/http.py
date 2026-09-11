"""The agent's own HTTP surface, alongside A2A."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread

from src.replies import with_footer


async def http_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Explain the custom routes this agent registers.

    An agent is an HTTP service as well as an A2A endpoint. Routers registered
    with ``app_registry.add_router()`` are mounted next to the built-in
    endpoints, which is where webhooks and health probes belong.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    await thread.reply(
        with_footer(
            "http",
            "Besides the A2A endpoint, this agent serves:",
            "  GET /showcase/commands            registered in src/api.py",
            "  GET /.well-known/agent-card.json  agent card, built from aion.yaml",
            "  GET /.well-known/configuration.json",
            "  GET /health/",
            "",
            "Through the proxy the same routes live under "
            "/agents/showcase/… — see docs.aion.to for the routing rules.",
        )
    )
