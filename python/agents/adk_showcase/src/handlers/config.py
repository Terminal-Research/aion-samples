"""Deployment configuration, as the control plane delivers it."""

from __future__ import annotations

from aion.adk.authoring.invocation import AionInvocationContext, Thread

from src.replies import with_footer


async def config_handler(ctx: AionInvocationContext, argument: str) -> None:
    """Report the configuration values bound to this deployment.

    Fields declared under ``configuration:`` in ``aion.yaml`` are filled in by
    an administrator per environment and arrive with the invocation, not from
    the process environment. Values declared as secrets arrive in plaintext, so
    treat them as sensitive: never log or echo them the way this sample echoes
    its non-secret ones.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)
    environment = ctx.aion_runtime_context.get_environment()

    if environment is None:
        await thread.reply(
            with_footer(
                "config",
                "This turn carries no environment: configuration is delivered by "
                "the control plane, and a direct local A2A call bypasses it. Deploy "
                "the agent and set `greeting` on the environment to see it here.",
            )
        )
        return

    variables = environment.configuration_variables or {}
    lines = [f"  {key} = {value}" for key, value in sorted(variables.items())] or ["  (none set)"]

    await thread.reply(
        with_footer(
            "config",
            f"Environment `{environment.name}` (project {environment.project_id}):",
            *lines,
            "",
            "These come from the `configuration:` block in aion.yaml, filled in per "
            "environment. Secret-typed values arrive here in plaintext — never echo "
            "those back the way this sample echoes the rest.",
        )
    )
