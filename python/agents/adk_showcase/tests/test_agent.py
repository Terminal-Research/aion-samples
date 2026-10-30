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
from src.handlers.hitl import QUESTION

SENT = {
    # The answer is text: one text artifact.
    "help": ["text"],
    "context": ["text"],
    "http": ["text"],
    "thinking": ["text"],
    "progress": ["text"],
    # The answer is streamed.
    "stream": ["stream"],
    # The result is something else; the explanation beside it is a message.
    "artifact": ["artifact", "message"],
    "file": ["artifact", "artifact", "message"],
    "data": ["artifact", "message"],
    "composite": ["artifact", "artifact", "message"],
    "metadata": ["message", "artifact", "message"],
    "task": ["message"],
    "message": ["message"],
    "card": ["message", "card", "card"],
    # A direct local turn: nothing to do, so a message says why.
    "llm": ["message"],
    "config": ["message"],
    "react": ["message"],
    # Messages by nature: a question, and the explanation of a failure.
    "ask": ["message"],
    "fail": ["message"],
}
"""What each command hands to ``thread.reply()`` on a direct local turn, in order."""


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


def _kind(content: object) -> str:
    if isinstance(content, str):
        return "message"
    if isinstance(content, Card):
        return "card"
    if _is_text_artifact(content):
        return "text"
    if isinstance(content, Artifact):
        return "artifact"
    if hasattr(content, "__aiter__"):
        return "stream"
    return type(content).__name__


def test_every_command_is_listed():
    assert set(SENT) == set(HANDLERS)


@pytest.mark.parametrize("key", sorted(HANDLERS))
def test_each_command_sends_its_result_and_explains_it_in_messages(key, sent):
    """Text is a text artifact only when it is the answer; text beside a result is a message.

    No handler yields a text event of its own, so nothing is sent twice. Every
    command except `stream`, whose footer is streamed with the answer, names
    its SDK call in a footer, in the text artifact or in a message.
    """
    events = _run(HANDLERS[key])

    contents = [content for content, _ in sent]
    assert [_kind(content) for content in contents] == SENT[key]
    assert all(event.content is None for event in events), f"{key} yielded a text event"

    if key != "stream":
        texts = [content if isinstance(content, str) else content.parts[0].text
                 for content in contents if _kind(content) in ("message", "text")]
        assert any("↳ " in text for text in texts), f"{key}: the answer lost its footer"


def test_the_answer_to_an_open_question_is_a_text_artifact(sent):
    """The turn that carries the answer to `ask` answers with a text artifact only."""
    events = _run(answer_handler, "staging")

    assert len(sent) == 1
    content, _ = sent[0]
    assert _is_text_artifact(content)
    assert '"staging"' in content.parts[0].text
    assert all(event.content is None for event in events)


def test_artifact_sends_a_hand_built_artifact(sent):
    """`artifact` sends its own artifact, with its metadata, before the message explaining it."""
    _run(HANDLERS["artifact"])

    (built, metadata), (explanation, _) = sent
    assert isinstance(built, Artifact) and built.name == HAND_BUILT_NAME
    assert built.artifact_id and len(built.parts) == 1 and built.parts[0].text
    assert metadata == HAND_BUILT_METADATA
    assert isinstance(explanation, str)
    assert built.artifact_id in explanation


def test_ask_sends_the_question_and_its_explanation_in_one_message(sent):
    _run(HANDLERS["ask"])

    (message, _), = sent
    assert message.startswith(QUESTION)
    assert "Reply with anything" in message
