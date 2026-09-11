"""Deployment configuration, as the control plane delivers it."""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langgraph.runtime import Runtime

from src.replies import with_footer
from src.state import AgentState


async def config_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Report the configuration values bound to this deployment.

    Fields declared under ``configuration:`` in ``aion.yaml`` are filled in by
    an administrator per environment and arrive with the invocation, not from
    the process environment. Values declared as secrets arrive in plaintext, so
    treat them as sensitive: never log or echo them the way this sample echoes
    its non-secret ones.
    """
    thread = Thread.from_context(runtime.context)
    environment = runtime.context.get_environment()

    if environment is None:
        reply = await thread.reply(
            with_footer(
                "config",
                "This turn carries no environment. Configuration reaches an agent "
                "with the invocation, not through the process environment, and a "
                "direct local A2A call carries none. Deploy the agent and set "
                "`greeting` on the environment to see the values here.",
            )
        )
        return {"messages": [reply]}

    variables = environment.configuration_variables or {}
    lines = [f"  {key} = {value}" for key, value in sorted(variables.items())] or ["  (none set)"]

    reply = await thread.reply(
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
    return {"messages": [reply]}
