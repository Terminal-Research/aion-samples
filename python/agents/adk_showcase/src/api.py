"""Custom HTTP routes served alongside the agent's A2A endpoint.

Anything registered here is mounted by the Aion server, next to the A2A
JSON-RPC endpoint, the agent card and the health check. The ``http`` command
tells the user how to call these.
"""

from aion.server import app_registry
from fastapi import APIRouter

from src.commands import COMMANDS

router = APIRouter(prefix="/showcase", tags=["Showcase Agent"])


@router.get("/commands")
async def list_commands() -> dict:
    """List every command the agent exposes, with the API each demonstrates."""
    return {
        "commands": [
            {
                "key": command.key,
                "summary": command.summary,
                "api": command.api,
                "source": command.source,
            }
            for command in COMMANDS
        ]
    }


app_registry.add_router(router)
