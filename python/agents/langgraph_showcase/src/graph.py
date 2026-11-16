"""The tour's graph: the event router reads the keyword, then that command's node answers."""

from __future__ import annotations

from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring import create_event_router
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from src.commands import COMMANDS, ask
from src.tour import TourState
from src.tour.routing import not_native, read_card_action, read_input, route


def create_graph() -> StateGraph:
    """Build the graph; the Aion server compiles and serves it."""
    workflow = StateGraph(TourState, context_schema=AionRuntimeContext)
    workflow.add_node(
        "events",
        create_event_router(on_message=read_input, on_invoke=read_input, on_card_action=read_card_action),
    )
    workflow.add_edge(START, "events")
    workflow.add_conditional_edges("events", route)

    for command in COMMANDS:
        workflow.add_node(command.COMMAND.key, command.with_sdk)
        if hasattr(command, "with_langgraph"):
            workflow.add_node(f"{command.COMMAND.key}_native", command.with_langgraph)
    workflow.add_node("not_native", not_native)

    # `ask` waits in a node of its own: LangGraph replays a node from its first
    # line when the graph resumes, so the explanation is sent in `ask` and the
    # wait happens in `ask_wait`.
    workflow.add_node("ask_wait", ask.wait)
    workflow.add_edge("ask", "ask_wait")

    for name in workflow.nodes:
        if name not in ("events", "ask"):
            workflow.add_edge(name, END)
    return workflow
