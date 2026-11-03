"""`config`: the configuration values of this deployment's environment.

The fields under ``configuration:`` in aion.yaml are filled in per environment
and arrive with the invocation, not from the process environment. Secret
values arrive in plaintext: never echo them.
"""

from __future__ import annotations

from aion.core.a2a import text_artifact
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.tour import Command, TourState

COMMAND = Command(
    key="config",
    summary="Configuration values the control plane passed to this deployment",
    api="context.get_environment()",
    no_native="deployment configuration comes from the platform",
)


async def with_sdk(state: TourState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Read the values from ``runtime.context.get_environment()``."""
    thread = Thread.from_context(runtime.context)
    environment = runtime.context.get_environment()
    if environment is None:
        await thread.reply(
            text_artifact(
                "A direct local call carries no environment. Deploy the agent and set `greeting` "
                "on its environment to see the values here." + COMMAND.footer
            )
        )
        return {}

    values = environment.configuration_variables or {}
    lines = [f"Environment `{environment.name}`:"] + (
        [f"  {key} = {value}" for key, value in sorted(values.items())] or ["  (none set)"]
    )
    await thread.reply(text_artifact("\n".join(lines) + COMMAND.footer))
    return {}


# No `with_langgraph`: deployment configuration comes from the platform, and `config native` says so.
