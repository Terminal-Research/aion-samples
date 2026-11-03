"""`<command> native`: each command done with ADK alone, or the reason it cannot be."""

import asyncio
import inspect
from types import SimpleNamespace

import pytest
from aion.adk.authoring.invocation import Thread
from aion.core.runtime import AionRuntimeContext
from google.genai import types

from src.commands import COMMANDS, artifact, attachment, context, fail, file, message, metadata, sections, stream
from src.tour.routing import not_native, parse_input

NATIVE = [module for module in COMMANDS if hasattr(module, "with_adk")]


def _ctx(user_content=None) -> SimpleNamespace:
    """An invocation context for a direct local turn."""
    return SimpleNamespace(
        aion_runtime_context=AionRuntimeContext(),
        agent=SimpleNamespace(name="showcase"),
        invocation_id="invocation-1",
        user_content=user_content,
        user_id="user-1",
        session=SimpleNamespace(id="session-1", state={}, events=[]),
    )


def _run(module, ctx: SimpleNamespace | None = None) -> list:
    """Run a command's ``with_adk`` to the end; return the ADK events it yielded."""
    result = module.with_adk(ctx or _ctx(), "")

    async def drain() -> list:
        if inspect.isasyncgen(result):
            return [event async for event in result]
        await result
        return []

    return asyncio.run(drain())


def _texts(events: list) -> list[str]:
    return [part.text for event in events if event.content for part in event.content.parts if part.text]


def test_every_command_but_help_says_whether_adk_can_do_it_alone():
    for module in COMMANDS:
        command = module.COMMAND
        if command.key == "help":
            assert command.native is None and command.no_native is None
        else:
            assert (command.native is None) != (command.no_native is None), command.key


def test_a_command_with_an_adk_version_says_how_it_works():
    for module in NATIVE:
        assert module.COMMAND.native, module.COMMAND.key


@pytest.mark.parametrize("module", NATIVE, ids=lambda module: module.COMMAND.key)
def test_the_adk_version_uses_nothing_of_the_sdk_or_the_tour(module):
    source = inspect.getsource(module.with_adk)
    for name in ("Thread", "thread.", "COMMAND", "footer"):
        assert name not in source


@pytest.mark.parametrize(
    ("text", "key", "native", "argument"),
    [
        ("stream", "stream", False, ""),
        ("stream native", "stream", True, ""),
        ("llm native What is A2A?", "llm", True, "What is A2A?"),
    ],
)
def test_native_is_the_word_right_after_the_keyword(text, key, native, argument):
    parsed = parse_input(text)
    assert (parsed.key, parsed.native, parsed.argument) == (key, native, argument)


def test_stream_yields_partial_events_then_the_whole_text():
    *partials, whole = _run(stream)

    assert partials and all(event.partial for event in partials)
    assert not whole.partial
    assert "".join(_texts(partials)) == whole.content.parts[0].text == stream.ANSWER


def test_sections_streams_two_runs_and_explains_in_a_text_event():
    wholes = [event for event in _run(sections) if not event.partial]

    assert [event.content.parts[0].text for event in wholes] == [
        sections.FIRST_SECTION,
        sections.SECOND_SECTION,
        sections.EXPLAINED,
    ]


def test_metadata_puts_custom_metadata_on_the_event():
    first, _ = _run(metadata)
    assert first.custom_metadata == {"showcase.step": "message", "showcase.run": "demo"}


def test_message_is_one_text_event():
    (event,) = _run(message)
    assert event.content.parts[0].text


def test_fail_raises_an_ordinary_exception():
    with pytest.raises(RuntimeError):
        _run(fail)


def test_context_shows_the_session_and_the_user():
    (event,) = _run(context)

    text = event.content.parts[0].text
    assert "session-1" in text and "user-1" in text


def test_attachment_lists_the_inline_data_of_the_user_content():
    content = types.Content(
        role="user",
        parts=[types.Part(text="attachment native"), types.Part(inline_data=types.Blob(mime_type="text/csv", data=b"a,b"))],
    )
    (event,) = _run(attachment, _ctx(user_content=content))

    text = event.content.parts[0].text
    assert "1 file(s)" in text
    assert "text/csv, 3 bytes inline" in text


@pytest.mark.parametrize(("module", "name"), [(artifact, "report"), (file, "units.csv")], ids=["artifact", "file"])
def test_artifact_and_file_save_through_the_artifact_service(module, name, monkeypatch):
    saved: list = []

    class FakeCallbackContext:
        def __init__(self, ctx, *, event_actions):
            self.actions = event_actions

        async def save_artifact(self, filename, artifact, custom_metadata=None):
            saved.append(filename)
            self.actions.artifact_delta[filename] = 0
            return 0

    monkeypatch.setattr(module, "CallbackContext", FakeCallbackContext)
    recorded, explained = _run(module)

    assert saved == [name]
    assert recorded.actions.artifact_delta == {name: 0}
    assert explained.content.parts[0].text


@pytest.mark.parametrize(
    "module", [module for module in COMMANDS if module.COMMAND.no_native], ids=lambda module: module.COMMAND.key
)
def test_not_native_says_why_and_names_the_sdk_call(module, monkeypatch):
    sent: list = []

    async def fake_reply(self, content, *, metadata=None):
        sent.append(content)

    monkeypatch.setattr(Thread, "reply", fake_reply)
    command = module.COMMAND
    asyncio.run(not_native(_ctx(), command.key))

    (text,) = sent
    assert command.no_native in text
    assert command.api in text
    assert text.endswith(command.footer.strip())
