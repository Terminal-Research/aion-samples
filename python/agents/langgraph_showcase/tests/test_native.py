"""`<command> native`: each command done with LangGraph alone, or the reason it cannot be."""

import asyncio
import base64
import inspect
from types import SimpleNamespace

import pytest
from aion.core.runtime import AionRuntimeContext
from langchain_core.messages import AIMessage, HumanMessage

from src.commands import COMMANDS, attachment, context, fail, file, message, sections, stream
from src.tour.routing import not_native, parse_input
from tests.support import message_text

NATIVE = [module for module in COMMANDS if hasattr(module, "with_langgraph")]


def test_every_command_but_help_says_whether_langgraph_can_do_it_alone():
    for module in COMMANDS:
        command = module.COMMAND
        if command.key == "help":
            assert command.native is None and command.no_native is None
        else:
            assert (command.native is None) != (command.no_native is None), command.key


def test_a_command_with_a_langgraph_version_says_how_it_works():
    for module in NATIVE:
        assert module.COMMAND.native, module.COMMAND.key


@pytest.mark.parametrize("module", NATIVE, ids=lambda module: module.COMMAND.key)
def test_the_langgraph_version_uses_nothing_of_the_sdk_or_the_tour(module):
    source = inspect.getsource(module.with_langgraph)
    for name in ("Thread", "thread.", "COMMAND", "footer"):
        assert name not in source


@pytest.mark.parametrize(
    ("text", "key", "native", "argument"),
    [
        ("stream", "stream", False, ""),
        ("stream native", "stream", True, ""),
        ("Show me the file NATIVE", "file", True, ""),
        ("llm native What is A2A?", "llm", True, "What is A2A?"),
        ("llm What is native code?", "llm", False, "What is native code?"),
    ],
)
def test_native_is_the_word_right_after_the_keyword(text, key, native, argument):
    parsed = parse_input(text)
    assert (parsed.key, parsed.native, parsed.argument) == (key, native, argument)


def test_stream_returns_what_the_chat_model_streamed():
    (answer,) = asyncio.run(stream.with_langgraph({"messages": [HumanMessage("stream native")]}))["messages"]

    assert isinstance(answer, AIMessage)
    assert answer.content == stream.ANSWER


def test_sections_calls_the_model_twice_and_explains_in_a_message():
    first, second, explained = asyncio.run(sections.with_langgraph({"messages": [HumanMessage("x")]}))["messages"]

    assert (first.content, second.content) == (sections.FIRST_SECTION, sections.SECOND_SECTION)
    assert explained.content == sections.EXPLAINED


def test_file_attaches_the_file_as_a_block_of_the_message():
    text, report = asyncio.run(file.with_langgraph({"messages": []}))["messages"][0].content

    assert text["type"] == "text"
    assert (report["type"], report["mime_type"], report["filename"]) == ("file", "text/csv", "units.csv")
    assert base64.b64decode(report["base64"]).decode() == file.REPORT


def test_message_returns_a_plain_ai_message():
    (answer,) = asyncio.run(message.with_langgraph({"messages": []}))["messages"]
    assert isinstance(answer, AIMessage)


def test_fail_raises_an_ordinary_exception():
    with pytest.raises(RuntimeError):
        asyncio.run(fail.with_langgraph({"messages": []}))


def test_context_shows_the_thread_id():
    update = asyncio.run(context.with_langgraph({"messages": []}, {"configurable": {"thread_id": "thread-7"}}))
    assert "thread-7" in update["messages"][0].content


def test_attachment_lists_the_file_blocks_of_the_message():
    inbound = HumanMessage(
        content=[
            {"type": "text", "text": "attachment native"},
            {"type": "file", "mime_type": "text/csv", "base64": base64.b64encode(b"a,b").decode()},
        ]
    )
    text = asyncio.run(attachment.with_langgraph({"messages": [inbound]}))["messages"][0].content

    assert "1 file(s)" in text
    assert "text/csv, a file block" in text


@pytest.mark.parametrize(
    "module", [module for module in COMMANDS if module.COMMAND.no_native], ids=lambda module: module.COMMAND.key
)
def test_not_native_says_why_and_names_the_sdk_call(module, replies):
    command = module.COMMAND
    state = {"messages": [], "command": command.key, "native": True}
    update = asyncio.run(not_native(state, runtime=SimpleNamespace(context=AionRuntimeContext())))

    text = message_text(replies[0])
    assert command.no_native in text
    assert command.api in text
    assert text.endswith(command.footer.strip())
    assert [kept.content for kept in update["messages"]] == [replies[0].content]
