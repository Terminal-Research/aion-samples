"""`config`: the configuration values of this deployment's environment.

The fields under ``configuration:`` in aion.yaml are filled in per environment
and arrive with the invocation, not from the process environment. Secret
values arrive in plaintext: never echo them.
"""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.core.a2a import text_artifact

from src.tour import Command

COMMAND = Command(
    key="config",
    summary="Configuration values the control plane passed to this deployment",
    api="context.get_environment()",
    no_native="deployment configuration comes from the platform",
)


async def with_sdk(ctx: AionInvocationContext, argument: str) -> None:
    """Read the values from ``ctx.aion_runtime_context.get_environment()``."""
    thread = Thread.from_context(ctx.aion_runtime_context)
    environment = ctx.aion_runtime_context.get_environment()
    if environment is None:
        await thread.reply(
            text_artifact(
                "A direct local call carries no environment. Deploy the agent and set `greeting` "
                "on its environment to see the values here." + COMMAND.footer
            )
        )
        return

    values = environment.configuration_variables or {}
    lines = [f"Environment `{environment.name}`:"] + (
        [f"  {key} = {value}" for key, value in sorted(values.items())] or ["  (none set)"]
    )
    await thread.reply(text_artifact("\n".join(lines) + COMMAND.footer))


# No `with_adk`: deployment configuration comes from the platform, and `config native` says so.
