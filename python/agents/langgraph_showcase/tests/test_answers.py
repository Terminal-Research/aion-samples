"""What each command sends: its result, and the messages beside it.

The nodes run with ``thread.reply()`` captured. A command whose answer is text
sends it as a text artifact and returns no message, because a returned
``AIMessage`` would reach the client as a message as well. A command whose
result is something else — files, data, a hand-built artifact, an explicit
Task, cards — sends its explanation as a message and keeps it in state. So
do the turns that do nothing but say why, and the texts that are messages by
nature: what `ask` says before it waits, the explanation of `fail`, the
messages `metadata` and `post` demonstrate.
"""

import asyncio
import re
from types import SimpleNamespace

import pytest
from a2a.types import Artifact, Message, Part, Role
from aion.core.a2a import A2AInbox
from aion.core.agent.invocation.card import Card
from aion.core.exceptions import TaskFailedError
from aion.core.runtime import AionRuntimeContext
from langchain_core.messages import HumanMessage

from src.commands import (
    BY_KEY,
    artifact,
    ask,
    attachment,
    card,
    composite,
    config,
    context,
    data,
    fail,
    file,
    help,
    http,
    message,
    metadata,
    post,
    progress,
    react,
    sections,
    stream,
    task,
    thinking,
)
from src.tour import standins
from src.tour.routing import parse_input, read_card_action
from tests.support import answer_text, message_text


def _run(node, command: str, context: AionRuntimeContext | None = None) -> dict:
    """Run one node for a direct A2A turn: no event, no environment, unless a context is given."""
    state = {"messages": [], "command": command, "input_text": command, "argument": ""}
    return asyncio.run(node(state, runtime=SimpleNamespace(context=context or AionRuntimeContext())))


def _footer(command: str) -> str:
    return BY_KEY[command].COMMAND.footer.strip()


def _kept(update: dict) -> list[str]:
    """The texts of the messages a node keeps in state."""
    return [message.content for message in update["messages"]]


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Drop the pauses `progress` and `stream` take for show."""
    monkeypatch.setattr(progress, "STEP_SECONDS", 0)
    monkeypatch.setattr(standins, "TYPEWRITER_DELAY_SECONDS", 0)


@pytest.mark.parametrize(
    ("command", "node"),
    [
        ("help", help.with_sdk),
        ("context", context.with_sdk),
        ("http", http.with_sdk),
        ("thinking", thinking.with_sdk),
        ("progress", progress.with_sdk),
    ],
)
def test_text_answer_is_one_text_artifact_and_no_message(command, node, replies):
    """A command whose answer is text sends one text artifact and returns no message."""
    update = _run(node, command)

    assert len(replies) == 1
    assert replies[0].content.name == "text"
    assert answer_text(replies[0]).endswith(_footer(command))
    assert update == {}


def test_every_text_artifact_is_a_new_artifact(replies):
    """Two answers are two artifacts, not one artifact sent twice."""
    _run(help.with_sdk, "help")
    _run(help.with_sdk, "help")

    assert replies[0].content.artifact_id != replies[1].content.artifact_id


@pytest.mark.parametrize(
    ("command", "node"),
    [
        ("config", config.with_sdk),
        ("react", react.with_sdk),
        ("attachment", attachment.with_sdk),
    ],
)
def test_a_turn_that_does_nothing_says_why_in_a_message(command, node, replies):
    """No environment, no distribution, no file: nothing is produced, so no artifact."""
    update = _run(node, command)

    assert len(replies) == 1
    assert message_text(replies[0]).endswith(_footer(command))
    assert _kept(update) == [replies[0].content]


def test_hand_built_artifact_keeps_every_field_and_is_explained_in_a_message(replies):
    """`artifact` sends an Artifact built field by field, then describes it in a message."""
    update = _run(artifact.with_sdk, "artifact")

    hand_built, explanation = replies
    assert isinstance(hand_built.content, Artifact)
    assert hand_built.content.artifact_id.startswith("hand-built-")
    assert hand_built.content.name == "hand-built"
    assert answer_text(hand_built)
    assert dict(hand_built.content.metadata) == {"showcase.kind": "hand-built"}

    text = message_text(explanation)
    assert hand_built.content.artifact_id in text
    assert "text_artifact" in text
    assert text.endswith(_footer("artifact"))
    assert _kept(update) == [text]


def test_cards_follow_their_explanation(replies):
    """The cards are the answer, so the explanation goes first and the cards close the turn."""
    update = _run(card.with_sdk, "card")

    assert message_text(replies[0]).endswith(_footer("card"))
    assert [type(reply.content) for reply in replies[1:]] == [Card, Card]
    assert _kept(update) == [replies[0].content]


@pytest.mark.parametrize(
    ("command", "node", "names"),
    [
        ("file", file.with_sdk, ["units.csv", "rfc9110.txt"]),
        ("data", data.with_sdk, ["totals"]),
    ],
)
def test_artifacts_are_explained_in_a_message(command, node, names, replies):
    """The artifacts are the result; the explanation after them is a message."""
    update = _run(node, command)

    assert [reply.content.name for reply in replies[:-1]] == names
    assert message_text(replies[-1]).endswith(_footer(command))
    assert _kept(update) == [replies[-1].content]


def test_composite_chunks_are_explained_in_a_message(monkeypatch, replies):
    events: list = []
    monkeypatch.setattr(composite, "get_stream_writer", lambda: events.append)

    update = _run(composite.with_sdk, "composite")

    assert len(events) == 3
    assert len({event.artifact.artifact_id for event in events}) == 1
    assert [event.append for event in events] == [False, True, True]
    assert [event.is_last_chunk for event in events] == [False, False, True]
    assert message_text(replies[0]).endswith(_footer("composite"))
    assert _kept(update) == [replies[0].content]


def test_ask_waits_on_the_question_and_answers_after_resume_with_an_artifact(monkeypatch, replies):
    """The explanation is a message kept in the conversation, the question is the interrupt
    value the input-required status shows, and what follows the resume is the task's answer."""
    asked = _run(ask.with_sdk, "ask")

    assert _kept(asked) == [message_text(replies[0])]
    assert ask.QUESTION not in replies[0].content

    interrupted: list = []

    def fake_interrupt(value):
        interrupted.append(value)
        return {"messages": [HumanMessage("staging")]}

    monkeypatch.setattr(ask, "interrupt", fake_interrupt)
    answered = _run(ask.wait, "ask")

    assert interrupted == [ask.QUESTION]
    assert 'continuing with "staging"' in answer_text(replies[1])
    assert answered == {}


def test_metadata_sends_its_message_its_data_and_an_explanation(replies):
    """The data artifact is the result; the message with metadata and the explanation are messages."""
    update = _run(metadata.with_sdk, "metadata")

    message, data, explanation = replies
    assert message_text(message) == "This message carries metadata."
    assert message.metadata == {"showcase.step": "message", "showcase.run": "demo"}
    assert data.content.name == "metadata_demo"
    assert data.metadata == {"showcase.step": "artifact"}
    assert message_text(explanation).endswith(_footer("metadata"))
    assert _kept(update) == [explanation.content]


def test_explicit_task_goes_to_the_outbox_and_is_explained_in_a_message(replies):
    update = _run(task.with_sdk, "task")

    built = update["a2a_outbox"].task
    assert built.artifacts[0].name == "explicit_artifact"
    assert built.history[0].parts[0].text == "First message of the explicit task history."
    assert dict(built.metadata) == {"built_by": "showcase"}
    assert message_text(replies[0]).endswith(_footer("task"))
    assert _kept(update) == [replies[0].content]


def test_explicit_message_goes_to_the_outbox_and_is_explained_in_a_message(replies):
    update = _run(message.with_sdk, "message")

    assert update["a2a_outbox"].message.parts[0].text == "An explicit A2A message, built by the agent."
    assert message_text(replies[0]).endswith(_footer("message"))
    assert _kept(update) == [replies[0].content]


def test_failure_is_explained_in_a_message_and_raised_with_its_reason(replies):
    """A failed task has no result: the explanation is a message, the reason is the error's."""
    with pytest.raises(TaskFailedError) as failure:
        _run(fail.with_sdk, "fail")

    assert failure.value.reason == fail.REASON
    assert len(replies) == 1
    assert message_text(replies[0]).endswith(_footer("fail"))


def test_stream_answers_through_the_stream(replies):
    """`stream` hands reply() an iterator; the streamed message is kept in state."""
    update = _run(stream.with_sdk, "stream")

    assert hasattr(replies[0].content, "__aiter__")
    assert update["messages"][0].content.endswith(_footer("stream"))


def test_thinking_shares_its_thoughts_before_the_answer(replies, thoughts):
    """Thoughts go through ``thread.thinking()``, not into a reply."""
    _run(thinking.with_sdk, "thinking")

    assert thoughts == ["Looking that up…", "Almost there…"]
    assert len(replies) == 1


def test_sections_streams_twice_around_a_thought(replies, thoughts):
    """Two streamed sections with a step between; both are kept in state, then explained."""
    update = _run(sections.with_sdk, "sections")

    first, second, explanation = replies
    assert hasattr(first.content, "__aiter__") and hasattr(second.content, "__aiter__")
    assert thoughts == ["Calling a tool…"]
    assert message_text(explanation).endswith(_footer("sections"))
    assert len(update["messages"]) == 3
    assert update["messages"][-1].content == explanation.content


def test_post_carries_no_route_and_the_reply_explains_it(replies):
    """`post` is called without a target; the explanation goes through `reply`."""
    update = _run(post.with_sdk, "post")

    posted, explanation = replies
    assert (posted.via, posted.target, posted.content) == ("post", None, post.POSTED)
    assert explanation.via == "reply"
    assert "direct A2A call" in message_text(explanation)
    assert message_text(explanation).endswith(_footer("post"))
    assert _kept(update) == [post.POSTED, explanation.content]


def test_attachment_describes_every_file_of_the_inbound_message(replies):
    """Inline bytes and a link are both files; the description is a text artifact."""
    inbound = Message(
        message_id="m-1",
        role=Role.ROLE_USER,
        parts=[
            Part(text="attachment"),
            Part(raw=b"date,units\n", filename="units.csv", media_type="text/csv"),
            Part(url="https://example.com/r.pdf", filename="r.pdf", media_type="application/pdf"),
        ],
    )

    update = _run(attachment.with_sdk, "attachment", AionRuntimeContext(inbox=A2AInbox(message=inbound)))

    text = answer_text(replies[0])
    assert "2 file(s)" in text
    assert "units.csv  text/csv, 11 bytes inline" in text
    assert "r.pdf  application/pdf, a link, https://example.com/r.pdf" in text
    assert text.endswith(_footer("attachment"))
    assert update == {}


def test_a_card_button_lands_on_the_command_it_names(replies):
    """Every button with an id names a command, and a press resolves to it."""
    _run(card.with_sdk, "card")

    ids = [
        found
        for reply in replies if isinstance(reply.content, Card)
        for found in re.findall(r'id="([^"]+)"', reply.content.jsx or "")
    ]
    assert ids
    for action_id in ids:
        assert parse_input(action_id).key == action_id
        pressed = asyncio.run(read_card_action(SimpleNamespace(payload=SimpleNamespace(action_id=action_id))))
        assert pressed["command"] == action_id
