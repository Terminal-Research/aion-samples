"""Graph assembly for the showcase agent.

Every turn enters through the Aion event router and leaves through the node
that demonstrates the resolved command. Nodes are named after the command they
handle, and each one is wired here by hand: adding a demonstration means adding
a registry entry, a node function, and one ``add_node``/``add_edge`` pair
below.
"""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring import create_event_router
from langgraph.constants import END, START
from langgraph.graph import StateGraph

import src.api  # registers the /showcase routes with the server
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
    llm_node,
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


def create_graph() -> StateGraph:
    """Build the showcase workflow.

    Returns:
        The assembled, uncompiled workflow.
    """
    workflow = StateGraph(AgentState, context_schema=AionRuntimeContext)

    workflow.add_node(
        "events",
        create_event_router(
            on_message=handle_input,
            on_invoke=handle_input,
            on_card_action=handle_card_action,
        ),
    )

    workflow.add_node("help", menu_node)
    workflow.add_node("stream", stream_node)
    workflow.add_node("llm", llm_node)
    workflow.add_node("typing", typing_node)
    workflow.add_node("card", card_node)
    workflow.add_node("file", file_node)
    workflow.add_node("data", data_node)
    workflow.add_node("composite", composite_node)
    workflow.add_node("ask", ask_node)
    workflow.add_node("ask_wait", ask_wait_node)
    workflow.add_node("react", react_node)
    workflow.add_node("metadata", metadata_node)
    workflow.add_node("progress", progress_node)
    workflow.add_node("task", task_node)
    workflow.add_node("message", message_node)
    workflow.add_node("fail", fail_node)
    workflow.add_node("context", context_node)
    workflow.add_node("config", config_node)
    workflow.add_node("http", http_node)

    workflow.add_edge(START, "events")
    workflow.add_conditional_edges("events", route_command)

    workflow.add_edge("help", END)
    workflow.add_edge("stream", END)
    workflow.add_edge("llm", END)
    workflow.add_edge("typing", END)
    workflow.add_edge("card", END)
    workflow.add_edge("file", END)
    workflow.add_edge("data", END)
    workflow.add_edge("composite", END)
    workflow.add_edge("react", END)
    workflow.add_edge("metadata", END)
    workflow.add_edge("progress", END)
    workflow.add_edge("task", END)
    workflow.add_edge("message", END)
    workflow.add_edge("fail", END)
    workflow.add_edge("context", END)
    workflow.add_edge("config", END)
    workflow.add_edge("http", END)

    # `ask` is the one two-node command. LangGraph replays a node from its
    # first line when the graph resumes, so the question is asked in one node
    # and the wait happens in the next: nothing gets sent twice.
    workflow.add_edge("ask", "ask_wait")
    workflow.add_edge("ask_wait", END)

    return workflow
