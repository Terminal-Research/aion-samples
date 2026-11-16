"""`http`: HTTP routes of the agent's own, served next to its A2A endpoint.

A router given to ``app_registry.add_router()`` is mounted by the Aion
server, beside the A2A endpoint, the agent card and the health check. That is
where webhooks and probes belong.
"""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact
from aion.server import app_registry
from fastapi import APIRouter

from src import commands
from src.tour import Command

COMMAND = Command(
    key="http",
    summary="Custom HTTP routes this agent serves next to A2A",
    api="app_registry.add_router()",
    no_native="the platform's server mounts the agent's HTTP routes",
)

router = APIRouter(prefix="/showcase", tags=["Showcase Agent"])


@router.get("/commands")
async def list_commands() -> dict:
    """Every command of the tour, with the SDK call it shows and how ADK does it alone."""
    return {
        "commands": [
            {
                "key": module.COMMAND.key,
                "summary": module.COMMAND.summary,
                "api": module.COMMAND.api,
                "native": module.COMMAND.native,
                "no_native": module.COMMAND.no_native,
                "source": module.COMMAND.source,
            }
            for module in commands.COMMANDS
        ]
    }


app_registry.add_router(router)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """List the routes this agent serves."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    routes = "\n".join(
        [
            "Besides the A2A endpoint, this agent serves:",
            "  GET /showcase/commands            registered in this file",
            "  GET /.well-known/agent-card.json  the agent card, built from aion.yaml",
            "  GET /.well-known/configuration.json",
            "  GET /health/",
            "",
            "Through the proxy the same routes live under /agents/showcase/.",
        ]
    )
    await thread.reply(text_artifact(routes + COMMAND.footer))


# No `with_adk`: the platform's server mounts the agent's HTTP routes, and `http native` says so.
