"""Dispatch tests, and what every handler sends — these import the Aion SDK and Google ADK."""

import asyncio
import inspect
from types import SimpleNamespace

import pytest
from a2a.types import Artifact
from aion.adk.authoring.invocation import Thread
from aion.core.agent.invocation.card import Card
from aion.core.runtime import AionRuntimeContext

from src.agent import HANDLERS, _inbound_text, create_agent
from src.commands import COMMANDS, parse_command
from src.handlers import answer_handler
from src.handlers import tasks as tasks_module
from src.handlers.artifacts import HAND_BUILT_METADATA, HAND_BUILT_NAME

MESSAGES = {
    "ask": 1,  # the question the turn leaves open
    "metadata": 1,  # the message that carries the metadata
    "fail": 1,  # the explanation of a task that fails, and so has no result
}
"""Commands that send a text message, and how many: a question, the message they
demonstrate, or the explanation of a failure."""

STREAMED = {"stream"}
"""Commands whose answer is a stream of chunks rather than a text artifact."""

FAILED = {"fail"}
"""Commands that end the task as failed: a failed task has no result, so they send no artifact."""


def test_every_command_has_a_handler():
    """The registry and the handler table stay in step."""
    assert set(HANDLERS) == {command.key for command in COMMANDS}


def test_every_handler_takes_the_context_and_an_argument():
    """One arity for all of them, so dispatch never branches on the command.

    The second parameter is the text typed after the keyword; handlers that
    accept none still take it and ignore it.
    """
    for key, handler in HANDLERS.items():
        parameters = list(inspect.signature(handler).parameters)
        assert len(parameters) == 2, f"{key}: {parameters}"
        assert parameters[0] == "ctx", f"{key}: {parameters}"


def test_agent_is_named_after_its_aion_yaml_entry():
    """The agent id in aion.yaml and the agent name match."""
    assert create_agent().name == "showcase"


def test_every_keyword_resolves_to_a_handler():
    """Anything the menu advertises can actually be dispatched."""
    for command in COMMANDS:
        resolved = parse_command(command.key)
        assert resolved is not None
        assert resolved.key in HANDLERS


def test_inbound_text_is_empty_without_a_runtime_context():
    """A turn with no Aion context falls through to the menu."""

    class _Ctx:
        aion_runtime_context = None

    assert _inbound_text(_Ctx()) == ""


def _ctx() -> SimpleNamespace:
    """An invocation context for a direct local turn: no inbound message, no environment."""
    return SimpleNamespace(
        aion_runtime_context=AionRuntimeContext(),
        session=SimpleNamespace(id="session-1", state={}, events=[]),
    )


@pytest.fixture
def sent(monkeypatch):
    """Capture what the handlers pass to ``thread.reply()``, with its metadata."""
    captured: list[tuple[object, dict | None]] = []

    async def fake_reply(self, content, *, metadata=None):
        captured.append((content, metadata))

    async def no_sleep(seconds):
        pass

    monkeypatch.setattr(Thread, "reply", fake_reply)
    monkeypatch.setattr(tasks_module.asyncio, "sleep", no_sleep)
    return captured


def _run(handler, argument: str = "") -> list:
    """Run one handler to the end; return the ADK events it yielded."""
    result = handler(_ctx(), argument)

    async def drain() -> list:
        if inspect.isasyncgen(result):
            return [event async for event in result]
        await result
        return []

    return asyncio.run(drain())


def _is_text_artifact(content: object) -> bool:
    return (
        isinstance(content, Artifact)
        and content.name == "text"
        and len(content.parts) == 1
        and content.parts[0].WhichOneof("content") == "text"
    )


@pytest.mark.parametrize("key", sorted(HANDLERS))
def test_every_answer_is_a_text_artifact(key, sent):
    """A command's text answer is the task's result: a text artifact, never a message.

    Messages are sent only where a command asks a question or demonstrates a
    message, and no handler yields a text event of its own, so no answer is
    also sent as a message beside its artifact.
    """
    events = _run(HANDLERS[key])

    contents = [content for content, _ in sent]
    texts = [content for content in contents if isinstance(content, str)]
    assert len(texts) == MESSAGES.get(key, 0), f"{key}: {texts}"
    assert all(event.content is None for event in events), f"{key} yielded a text event"

    if key in STREAMED:
        assert hasattr(contents[-1], "__aiter__")
        assert not any(isinstance(content, Artifact) for content in contents)
    elif key in FAILED:
        assert not any(isinstance(content, Artifact) for content in contents)
    else:
        assert _is_text_artifact(contents[-1]), f"{key} ends with {contents[-1]!r}"
        assert "↳ " in contents[-1].parts[0].text, f"{key}: the answer lost its footer"


def test_the_answer_to_an_open_question_is_a_text_artifact(sent):
    """The turn that carries the answer to `ask` answers with a text artifact only."""
    events = _run(answer_handler, "staging")

    assert len(sent) == 1
    content, _ = sent[0]
    assert _is_text_artifact(content)
    assert '"staging"' in content.parts[0].text
    assert all(event.content is None for event in events)


def test_artifact_sends_a_hand_built_artifact(sent):
    """`artifact` sends its own artifact, with its metadata, before the text artifact explaining it."""
    _run(HANDLERS["artifact"])

    (built, metadata), (explanation, _) = sent
    assert isinstance(built, Artifact) and built.name == HAND_BUILT_NAME
    assert built.artifact_id and len(built.parts) == 1 and built.parts[0].text
    assert metadata == HAND_BUILT_METADATA
    assert _is_text_artifact(explanation)
    assert built.artifact_id in explanation.parts[0].text


def test_cards_stay_cards(sent):
    """`card` still sends its two cards; only its explanation is a text artifact."""
    _run(HANDLERS["card"])

    assert [type(content) for content, _ in sent[:2]] == [Card, Card]
