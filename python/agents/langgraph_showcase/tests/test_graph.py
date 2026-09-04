"""Graph assembly tests — these import the Aion SDK."""

from src.commands import COMMANDS
from src.graph import ASK_WAIT_NODE, EVENTS_NODE, NODE_FUNCTIONS, create_graph
from src.router import route_command


def test_every_command_has_a_node_function():
    """The registry and the node table stay in step."""
    assert set(NODE_FUNCTIONS) == {command.key for command in COMMANDS}


def test_graph_contains_a_node_per_command():
    """Each command is reachable as its own node."""
    graph = create_graph().compile()
    nodes = set(graph.get_graph().nodes)

    assert EVENTS_NODE in nodes
    assert ASK_WAIT_NODE in nodes
    for command in COMMANDS:
        assert command.node in nodes


def test_routing_targets_existing_nodes():
    """Routing returns node names the graph actually has."""
    nodes = set(create_graph().compile().get_graph().nodes)

    for command in COMMANDS:
        assert route_command({"command": command.key}) in nodes
    assert route_command({"command": None}) == "cmd_help"
