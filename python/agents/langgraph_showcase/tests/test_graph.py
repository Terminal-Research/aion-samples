"""The tour's graph: a node per command, and routing that lands on one."""

import pytest

from src.commands import COMMANDS
from src.graph import create_graph
from src.tour.routing import route


def _nodes() -> set[str]:
    return set(create_graph().compile().get_graph().nodes)


def test_graph_has_a_node_per_command_and_per_native_version():
    nodes = _nodes()

    assert {"events", "ask_wait", "not_native"} <= nodes
    for module in COMMANDS:
        assert module.COMMAND.key in nodes
        if hasattr(module, "with_langgraph"):
            assert f"{module.COMMAND.key}_native" in nodes


@pytest.mark.parametrize("native", [False, True])
def test_routing_lands_on_a_node_the_graph_has(native):
    nodes = _nodes()

    for module in COMMANDS:
        assert route({"command": module.COMMAND.key, "native": native}) in nodes
    assert route({"command": None, "native": native}) == "help"


def test_native_runs_with_langgraph_the_command_itself_or_says_it_cannot():
    for module in COMMANDS:
        key = module.COMMAND.key
        target = route({"command": key, "native": True})
        if hasattr(module, "with_langgraph"):
            assert target == f"{key}_native"
        elif module.COMMAND.no_native:
            assert target == "not_native"
        else:
            assert target == key
