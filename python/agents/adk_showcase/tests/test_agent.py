"""Dispatch tests, and what every handler sends — these import the Aion SDK and Google ADK."""

import asyncio
import inspect
import re
from types import SimpleNamespace

import pytest
from a2a.types import Artifact, Message, Part, Role
from aion.adk.authoring.invocation import Thread
from aion.core.a2a import A2AInbox
from aion.core.agent.invocation.card import Card
from aion.core.exceptions import TaskFailedError
from aion.core.runtime import AionRuntimeContext
from google.genai import types

from src.agent import create_agent
from src.commands import BY_KEY, COMMANDS, ask, composite, progress
from src.commands.ask import QUESTION, REQUEST_INPUT, answered_question
from src.commands.fail import REASON as FAIL_REASON
from src.commands.post import POSTED
from src.tour import standins
from src.tour.routing import inbound_text as _inbound_text
from src.tour.routing import parse_input

HANDLERS = {key: module.with_sdk for key, module in BY_KEY.items()}
"""The SDK version of every command, by its key."""

SENT = {
    # The answer is text: one text artifact.
    "help": ["text"],
    "context": ["text"],
    "http": ["text"],
    "thinking": ["text"],
    "progress": ["text"],
    # The answer is streamed.
    "stream": ["stream"],
    "sections": ["stream", "stream", "message"],
    # The result is something else; the explanation beside it is a message.
    "artifact": ["artifact", "message"],
    "file": ["artifact", "artifact", "message"],
    "data": ["artifact", "message"],
    "composite": ["message"],
    "metadata": ["message", "artifact", "message"],
    "task": ["message"],
    "message": ["message"],
    "card": ["message", "card", "card"],
    # A direct local turn: nothing to do, so the answer says why.
    "llm": ["text"],
    "config": ["text"],
    "react": ["text"],
    "attachment": ["text"],
    # Messages by nature: what `ask` says before it waits, the explanation of a
    # failure, and the posted message beside its explanation.
    "ask": ["message"],
    "fail": ["message"],
    "post": ["message", "message"],
}
"""What each command hands to ``thread.reply()`` on a direct local turn, in order."""


def test_every_command_has_a_handler():
    """Every command file has an SDK version."""
    assert set(HANDLERS) == {module.COMMAND.key for module in COMMANDS}


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
    for module in COMMANDS:
        resolved = parse_input(module.COMMAND.key)
        assert resolved is not None
        assert resolved.key in HANDLERS


def test_inbound_text_is_empty_without_a_runtime_context():
    """A turn with no Aion context falls through to the menu."""

    class _Ctx:
        aion_runtime_context = None

    assert _inbound_text(_Ctx()) == ""


def _ctx(runtime: AionRuntimeContext | None = None, user_content=None) -> SimpleNamespace:
    """An invocation context for a direct local turn: no inbound message, no environment."""
    return SimpleNamespace(
        aion_runtime_context=runtime or AionRuntimeContext(),
        agent=SimpleNamespace(name="showcase"),
        user_content=user_content,
        session=SimpleNamespace(id="session-1", state={}, events=[]),
    )


@pytest.fixture
def sent(monkeypatch):
    """Capture what the handlers pass to ``thread.reply()`` and ``thread.post()``, with its metadata."""
    captured: list[tuple[object, dict | None]] = []

    async def fake_reply(self, content, *, metadata=None):
        captured.append((content, metadata))

    async def fake_post(self, content, *, target=None, metadata=None):
        captured.append((content, {"via": "post", "target": target}))

    async def no_sleep(seconds):
        pass

    monkeypatch.setattr(Thread, "reply", fake_reply)
    monkeypatch.setattr(Thread, "post", fake_post)
    monkeypatch.setattr(progress.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(standins, "TYPEWRITER_DELAY_SECONDS", 0)
    # `composite` appends its chunks through the emitter of a running invocation.
    monkeypatch.setattr(composite, "get_adk_emitter", lambda: [].append)
    return captured


@pytest.fixture
def thoughts(monkeypatch) -> list[str]:
    """Capture what the handlers pass to ``thread.thinking()``."""
    captured: list[str] = []

    async def fake_thinking(self, content, *, metadata=None):
        captured.append(content)

    monkeypatch.setattr(Thread, "thinking", fake_thinking)
    return captured


def _run(handler, argument: str = "", ctx: SimpleNamespace | None = None) -> list:
    """Run one handler to the end; return the ADK events it yielded."""
    result = handler(ctx or _ctx(), argument)

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
    its SDK call in a footer, in the text artifact or in a message. `fail`
    raises once its explanation is out.
    """
    if key == "fail":
        with pytest.raises(TaskFailedError):
            _run(HANDLERS[key])
        events = []
    else:
        events = _run(HANDLERS[key])

    contents = [content for content, _ in sent]
    assert [_kind(content) for content in contents] == SENT[key]
    texts_yielded = [
        part.text for event in events if event.content for part in event.content.parts if part.text
    ]
    assert not texts_yielded, f"{key} yielded a text event"

    if key != "stream":
        texts = [content if isinstance(content, str) else content.parts[0].text
                 for content in contents if _kind(content) in ("message", "text")]
        assert any("↳ " in text for text in texts), f"{key}: the answer lost its footer"


def test_the_answer_to_an_open_question_is_a_text_artifact(sent):
    """The turn that carries the answer to `ask` answers with a text artifact only."""
    events = _run(ask.answer, "staging")

    assert len(sent) == 1
    content, _ = sent[0]
    assert _is_text_artifact(content)
    assert '"staging"' in content.parts[0].text
    assert all(event.content is None for event in events)


def test_artifact_sends_a_hand_built_artifact(sent):
    """`artifact` sends its own artifact, metadata inside it, before the message explaining it."""
    _run(HANDLERS["artifact"])

    (built, metadata), (explanation, _) = sent
    assert isinstance(built, Artifact) and built.name == "hand-built"
    assert built.artifact_id and len(built.parts) == 1 and built.parts[0].text
    assert dict(built.metadata) == {"showcase.kind": "hand-built"}
    assert metadata is None
    assert isinstance(explanation, str)
    assert built.artifact_id in explanation


def test_ask_explains_then_pauses_on_a_long_running_call(sent):
    """The explanation is a message; the question is the `adk_request_input` call the run waits on."""
    (event,) = _run(HANDLERS["ask"])

    (message, _), = sent
    assert QUESTION not in message and "Reply with anything" in message
    (call,) = event.get_function_calls()
    assert (call.name, call.args) == (REQUEST_INPUT, {"message": QUESTION})
    assert event.long_running_tool_ids == {call.id}
    assert event.author == "showcase"


def _resumed(response: dict) -> types.Content:
    """The user content of a turn that answers the `ask` call."""
    return types.Content(
        role="user",
        parts=[types.Part(function_response=types.FunctionResponse(id="call-1", name=REQUEST_INPUT, response=response))],
    )


def test_the_answer_is_read_from_the_function_response():
    """Plain text arrives as `result`; any other turn answers no question."""
    assert answered_question(_ctx(user_content=_resumed({"result": "staging"}))) == "staging"
    assert answered_question(_ctx(user_content=_resumed({"env": "prod"}))) == '{"env": "prod"}'
    assert answered_question(_ctx(user_content=types.Content(role="user", parts=[types.Part(text="ask")]))) is None
    assert answered_question(_ctx()) is None


def test_a_resumed_turn_goes_to_the_answer_not_to_a_command(sent):
    """The reply resumes `ask`, even though its text would not name a command."""
    ctx = _ctx(user_content=_resumed({"result": "staging"}))

    async def drain():
        return [event async for event in create_agent()._run_async_impl(ctx)]

    assert asyncio.run(drain()) == []
    (content, _), = sent
    assert _is_text_artifact(content) and '"staging"' in content.parts[0].text


def test_fail_explains_then_raises_its_reason(sent):
    with pytest.raises(TaskFailedError) as failure:
        _run(HANDLERS["fail"])

    assert failure.value.reason == FAIL_REASON
    (message, _), = sent
    assert message.endswith(BY_KEY["fail"].COMMAND.footer.strip())


def test_thinking_shares_its_thoughts_before_the_answer(sent, thoughts):
    _run(HANDLERS["thinking"])

    assert thoughts == ["Looking that up…", "Almost there…"]
    assert len(sent) == 1


def test_sections_streams_twice_around_a_thought(sent, thoughts):
    _run(HANDLERS["sections"])

    assert thoughts == ["Calling a tool…"]
    assert [_kind(content) for content, _ in sent] == ["stream", "stream", "message"]


def test_post_carries_no_route_and_the_reply_explains_it(sent):
    _run(HANDLERS["post"])

    (posted, how), (explanation, reply_metadata) = sent
    assert (posted, how) == (POSTED, {"via": "post", "target": None})
    assert reply_metadata is None
    assert "direct A2A call" in explanation


def test_composite_appends_three_chunks_to_one_artifact(sent, monkeypatch):
    emitted: list = []
    monkeypatch.setattr(composite, "get_adk_emitter", lambda: emitted.append)

    _run(HANDLERS["composite"])

    published = [event.custom_metadata["aion:output"]["published"] for event in emitted]
    assert len({chunk["artifact"]["artifact_id"] for chunk in published}) == 1
    assert [chunk["append"] for chunk in published] == [False, True, True]
    assert [chunk["last_chunk"] for chunk in published] == [False, False, True]
    assert [_kind(content) for content, _ in sent] == ["message"]


def test_attachment_describes_every_file_of_the_inbound_message(sent):
    inbound = Message(
        message_id="m-1",
        role=Role.ROLE_USER,
        parts=[
            Part(text="attachment"),
            Part(raw=b"date,units\n", filename="units.csv", media_type="text/csv"),
            Part(url="https://example.com/r.pdf", filename="r.pdf", media_type="application/pdf"),
        ],
    )

    _run(HANDLERS["attachment"], ctx=_ctx(AionRuntimeContext(inbox=A2AInbox(message=inbound))))

    (content, _), = sent
    assert _is_text_artifact(content)
    text = content.parts[0].text
    assert "2 file(s)" in text
    assert "units.csv  text/csv, 11 bytes inline" in text
    assert "r.pdf  application/pdf, a link, https://example.com/r.pdf" in text


def test_a_card_button_lands_on_the_command_it_names(sent):
    """Every button with an id names a command, and a press resolves to it."""
    _run(HANDLERS["card"])

    ids = [
        found
        for content, _ in sent if isinstance(content, Card)
        for found in re.findall(r'id="([^"]+)"', content.jsx or "")
    ]
    assert ids
    for action_id in ids:
        assert parse_input(action_id).key == action_id
        pressed = SimpleNamespace(
            aion_runtime_context=SimpleNamespace(event=SimpleNamespace(payload=SimpleNamespace(action_id=action_id)))
        )
        assert _inbound_text(pressed) == action_id
