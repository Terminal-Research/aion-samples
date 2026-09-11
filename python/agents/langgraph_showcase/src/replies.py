"""The footer every reply ends with."""

from __future__ import annotations

from src.commands import COMMANDS_BY_KEY


def with_footer(command_key: str, *lines: str) -> str:
    """Join the reply lines and append the command's source footer.

    The footer is what turns the agent into a browsable index of the platform:
    every answer states which SDK call produced it and where that call lives.
    Sending the text is left to the caller, so the SDK call the footer names is
    the one written in the node itself.

    Args:
        command_key: Key of the command being demonstrated.
        *lines: Body lines of the reply.

    Returns:
        The reply text, footer included.
    """
    return "\n".join([*lines, "", COMMANDS_BY_KEY[command_key].footer()])
