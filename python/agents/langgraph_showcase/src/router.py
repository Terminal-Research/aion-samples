"""Inbound routing: resolve free-form text to a command, then to a node."""

from __future__ import annotations

from src.commands import MENU_COMMAND, parse_command, parse_input
from src.state import AgentState


async def handle_input(message) -> dict:
    """Entry handler for every inbound turn.

    Registered for both event-carried messages (an inbound distribution) and
    plain A2A invocations, so the same agent works either way.

    Args:
        message: Normalized inbound message, or None when the turn carries none.

    Returns:
        A state update with the resolved command key and the raw input text.
    """
    text = getattr(message, "text", None) if message is not None else None
    parsed = parse_input(text)
    return {
        "command": parsed.command.key if parsed.command else None,
        "input_text": text,
        "argument": parsed.argument,
    }


def route_command(state: AgentState) -> str:
    """Return the node that handles the resolved command.

    Unrecognized input falls through to the menu, which quotes what was sent.
    """
    command_key = state.get("command")
    if command_key is None:
        return MENU_COMMAND.node
    return f"cmd_{command_key}"


async def handle_card_action(event) -> dict:
    """Entry handler for a button press on a card this agent sent.

    Card buttons carry a developer-defined ``action_id``. This agent uses the
    command key as the action id, so a press lands on exactly the same node as
    typing that keyword.

    Args:
        event: Inbound Aion event carrying a card-action payload.

    Returns:
        A state update with the resolved command key.
    """
    action_id = getattr(event.payload, "action_id", None) if event and event.payload else None
    command = parse_command(action_id)
    return {
        "command": command.key if command else None,
        "input_text": action_id,
        "argument": "",
    }
