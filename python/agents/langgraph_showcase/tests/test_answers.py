"""Every answer is the task's result: a text artifact, with no message beside it.

The nodes run with ``thread.reply()`` captured. A node that answers with an
artifact returns no message, because a returned ``AIMessage`` would reach the
client as a message as well. The texts that stay messages — the question
`ask` asks, the explanation of `fail`, the message `metadata` demonstrates —
are checked to be plain text replies.
"""

import asyncio
from types import SimpleNamespace

import pytest
from a2a.types import Artifact, TaskState
from aion.core.agent.invocation.card import Card
from aion.core.runtime import AionRuntimeContext
from langchain_core.messages import HumanMessage

from src.commands import COMMANDS_BY_KEY
from src.nodes import (
    artifact_node,
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
    thinking_node,
)
from src.nodes import artifacts as artifacts_module
from src.nodes import hitl as hitl_module
from src.nodes import messaging as messaging_module
from src.nodes import tasks as tasks_module
from tests.support import answer_text


def _run(node, command: str) -> dict:
    """Run one node for a direct A2A turn: no event, no environment."""
    state = {"messages": [], "command": command, "input_text": command, "argument": ""}
    return asyncio.run(node(state, runtime=SimpleNamespace(context=AionRuntimeContext())))


def _footer(command: str) -> str:
    return COMMANDS_BY_KEY[command].footer()


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Drop the pauses `progress` and `stream` take for show."""
    monkeypatch.setattr(tasks_module, "STEP_SECONDS", 0)
    monkeypatch.setattr(messaging_module, "TYPEWRITER_DELAY_SECONDS", 0)


@pytest.mark.parametrize(
    ("command", "node"),
    [
        ("help", menu_node),
        ("config", config_node),
        ("context", context_node),
        ("http", http_node),
        ("thinking", thinking_node),
        ("react", react_node),
        ("progress", progress_node),
    ],
)
def test_answer_is_one_text_artifact_and_no_message(command, node, replies):
    """A command that only answers sends one text artifact and returns no message."""
    update = _run(node, command)

    assert len(replies) == 1
    assert replies[0].content.name == "text"
    assert answer_text(replies[0]).endswith(_footer(command))
    assert update == {}


def test_every_text_artifact_is_a_new_artifact(replies):
    """Two answers are two artifacts, not one artifact sent twice."""
    _run(menu_node, "help")
    _run(menu_node, "help")

    assert replies[0].content.artifact_id != replies[1].content.artifact_id


def test_hand_built_artifact_keeps_every_field_it_was_given(replies):
    """`artifact` sends an Artifact built field by field, then explains it in a text artifact."""
    update = _run(artifact_node, "artifact")

    hand_built, explanation = (reply.content for reply in replies)
    assert isinstance(hand_built, Artifact)
    assert hand_built.artifact_id.startswith("hand-built-")
    assert hand_built.name == "hand-built"
    assert answer_text(replies[0])
    assert dict(hand_built.metadata) == {"showcase.kind": "hand-built"}

    text = answer_text(replies[1])
    assert explanation.name == "text"
    assert hand_built.artifact_id in text
    assert "text_artifact" in text
    assert text.endswith(_footer("artifact"))
    assert update == {}


def test_cards_are_followed_by_a_text_answer(replies):
    update = _run(card_node, "card")

    assert [type(reply.content) for reply in replies[:2]] == [Card, Card]
    assert answer_text(replies[2]).endswith(_footer("card"))
    assert update == {}


@pytest.mark.parametrize(
    ("command", "node", "names"),
    [
        ("file", file_node, ["units.csv", "rfc9110.txt"]),
        ("data", data_node, ["totals"]),
    ],
)
def test_artifacts_are_followed_by_a_text_answer(command, node, names, replies):
    """The demonstrated artifacts go out unchanged, and the explanation is one more artifact."""
    update = _run(node, command)

    assert [reply.content.name for reply in replies[:-1]] == names
    assert answer_text(replies[-1]).endswith(_footer(command))
    assert update == {}


def test_composite_chunks_are_followed_by_a_text_answer(monkeypatch, replies):
    events: list = []
    monkeypatch.setattr(artifacts_module, "get_stream_writer", lambda: events.append)

    update = _run(composite_node, "composite")

    assert len(events) == 3
    assert len({event.artifact.artifact_id for event in events}) == 1
    assert answer_text(replies[0]).endswith(_footer("composite"))
    assert update == {}


def test_ask_question_is_a_message_and_the_answer_after_resume_is_an_artifact(monkeypatch, replies):
    """The question stays in the conversation; what follows the resume is the task's answer."""
    asked = _run(ask_node, "ask")

    assert isinstance(replies[0].content, str)
    assert [message.content for message in asked["messages"]] == [replies[0].content]

    monkeypatch.setattr(hitl_module, "interrupt", lambda value: {"messages": [HumanMessage("staging")]})
    answered = _run(ask_wait_node, "ask")

    assert 'continuing with "staging"' in answer_text(replies[1])
    assert answered == {}


def test_metadata_keeps_its_message_and_explains_in_an_artifact(replies):
    """The message with metadata is the demonstration; the explanation is a text artifact."""
    update = _run(metadata_node, "metadata")

    message, data, explanation = replies
    assert isinstance(message.content, str)
    assert message.metadata == {"showcase.step": "message", "showcase.run": "demo"}
    assert data.content.name == "metadata_demo"
    assert data.metadata == {"showcase.step": "artifact"}
    assert answer_text(explanation).endswith(_footer("metadata"))
    assert update == {}


def test_explicit_task_goes_to_the_outbox_and_the_explanation_is_an_artifact(replies):
    update = _run(task_node, "task")

    assert set(update) == {"a2a_outbox"}
    assert update["a2a_outbox"].task.artifacts[0].name == "explicit_artifact"
    assert answer_text(replies[0]).endswith(_footer("task"))


def test_explicit_message_goes_to_the_outbox_and_the_explanation_is_an_artifact(replies):
    update = _run(message_node, "message")

    assert set(update) == {"a2a_outbox"}
    assert update["a2a_outbox"].message.parts[0].text == "An explicit A2A message, built by the agent."
    assert answer_text(replies[0]).endswith(_footer("message"))


def test_failure_is_explained_in_a_message(replies):
    """A failed task has no result, so its explanation stays a message."""
    update = _run(fail_node, "fail")

    assert isinstance(replies[0].content, str)
    assert update["a2a_outbox"].task.status.state == TaskState.TASK_STATE_FAILED
    assert [message.content for message in update["messages"]] == [replies[0].content]


def test_stream_answers_through_the_stream(replies):
    """`stream` hands reply() an iterator; the streamed message is kept in state."""
    update = _run(stream_node, "stream")

    assert hasattr(replies[0].content, "__aiter__")
    assert update["messages"][0].content.endswith(_footer("stream"))
