"""`http`: HTTP routes of the agent's own, served next to its A2A endpoint.

A router given to ``app_registry.add_router()`` is mounted by the Aion
server, beside the A2A endpoint, the agent card and the health check. That is
where webhooks and probes belong.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from aion.server import app_registry
from fastapi import APIRouter
from langgraph.runtime import Runtime

from src import commands
from src.tour import Command, TourState

COMMAND = Command(
    key="http",
    summary="Custom HTTP routes this agent serves next to A2A",
    api="app_registry.add_router()",
    no_native="the platform's server mounts the agent's HTTP routes",
)

router = APIRouter(prefix="/showcase", tags=["Showcase Agent"])


@router.get("/commands")
async def list_commands() -> dict:
    """Every command of the tour, with the SDK call it shows and how LangGraph does it alone."""
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


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """List the routes this agent serves."""
    thread = Thread.from_context(runtime.context)
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
    return {}


# No `with_langgraph`: the platform's server mounts the agent's HTTP routes, and `http native` says so.
