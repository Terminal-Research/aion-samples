"""Graph assembly tests — these import the Aion SDK."""

from src.commands import COMMANDS
from src.graph import create_graph
from src.router import route_command


def test_graph_contains_a_node_per_command():
    """Each command is reachable as a node named after its keyword."""
    graph = create_graph().compile()
    nodes = set(graph.get_graph().nodes)

    assert "events" in nodes
    assert "ask_wait" in nodes
    for command in COMMANDS:
        assert command.key in nodes


def test_routing_targets_existing_nodes():
    """Routing returns node names the graph actually has."""
    nodes = set(create_graph().compile().get_graph().nodes)

    for command in COMMANDS:
        assert route_command({"command": command.key}) in nodes
    assert route_command({"command": None}) == "help"
