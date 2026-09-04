"""Graph assembly for the showcase agent.

The graph is generated from the command registry: every entry in
``src.commands.COMMANDS`` becomes one node, wired to the router. Adding a
demonstration means adding a registry entry and a node function — the menu, the
HTTP listing and the agent card examples follow from the same source.
"""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring import create_event_router
from aion.server import app_registry
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from src.api import router as http_router
from src.commands import COMMANDS
from src.nodes import (
    ask_node,
    ask_wait_node,
    card_node,
    composite_node,
    config_node,
    context_node,
    data_node,
    fail_node,
    file_node,
    http_node,
    menu_node,
    message_node,
    metadata_node,
    progress_node,
    react_node,
    stream_node,
    task_node,
    typing_node,
)
from src.router import handle_card_action, handle_input, route_command
from src.state import AgentState

EVENTS_NODE = "aion_events"
ASK_WAIT_NODE = "cmd_ask_wait"

NODE_FUNCTIONS = {
    "help": menu_node,
    "stream": stream_node,
    "typing": typing_node,
    "card": card_node,
    "file": file_node,
    "data": data_node,
    "composite": composite_node,
    "ask": ask_node,
    "react": react_node,
    "metadata": metadata_node,
    "progress": progress_node,
    "task": task_node,
    "message": message_node,
    "fail": fail_node,
    "context": context_node,
    "config": config_node,
    "http": http_node,
}


def create_graph() -> StateGraph:
    """Build the showcase workflow.

    Every turn enters through the Aion event router, which resolves the inbound
    text (or card button press) to a command, and leaves through the node that
    demonstrates it. Unrecognized input goes to the menu.

    Returns:
        The assembled, uncompiled workflow.
    """
    workflow = StateGraph(AgentState, context_schema=AionRuntimeContext)

    workflow.add_node(
        EVENTS_NODE,
        create_event_router(
            on_message=handle_input,
            on_invoke=handle_input,
            on_card_action=handle_card_action,
        ),
    )

    for command in COMMANDS:
        workflow.add_node(command.node, NODE_FUNCTIONS[command.key])
    workflow.add_node(ASK_WAIT_NODE, ask_wait_node)

    workflow.add_edge(START, EVENTS_NODE)
    workflow.add_conditional_edges(EVENTS_NODE, route_command)

    for command in COMMANDS:
        # `ask` is the one two-node command: it asks, then waits in a node of
        # its own so the question is not re-emitted when the graph resumes.
        if command.key != "ask":
            workflow.add_edge(command.node, END)
    workflow.add_edge("cmd_ask", ASK_WAIT_NODE)
    workflow.add_edge(ASK_WAIT_NODE, END)

    return workflow


app_registry.add_router(http_router)
