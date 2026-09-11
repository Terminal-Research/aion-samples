"""The `llm` node — model choice and failure handling, with the model faked."""

import asyncio
from types import SimpleNamespace

import pytest
from aion.core.a2a.extensions.distribution import (
    Behavior,
    Distribution,
    DistributionExtensionV1,
    Environment,
)
from aion.api.exceptions import AionAuthenticationError
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from langchain_core.messages import AIMessage, AIMessageChunk

from src.nodes import llm as llm_module
from src.nodes.llm import DEFAULT_MODEL, USAGE, llm_node

ANSWER_CHUNKS = ("Hello", ", ", "world")


def _runtime(configuration: dict[str, str] | None = None) -> SimpleNamespace:
    """Build a runtime whose context carries an environment, or none at all."""
    payload = None
    if configuration is not None:
        payload = DistributionExtensionV1(
            distribution=Distribution(
                id="dist-1", endpoint_type="A2A", url="test://distribution", identities=[]
            ),
            behavior=Behavior(id="beh-1", behavior_key="showcase", version_id="v-1"),
            environment=Environment(
                id="env-1",
                name="test",
                project_id="proj-1",
                deployment_id="dep-1",
                configuration_variables=configuration,
            ),
        )
    return SimpleNamespace(context=AionRuntimeContext(distribution_extension_payload=payload))


def _state(argument: str) -> dict:
    return {"messages": [], "command": "llm", "input_text": f"llm {argument}", "argument": argument}


class _FakeChat:
    """Stands in for the chat model: streams fixed chunks or fails."""

    def __init__(self, error: BaseException | None = None):
        self.error = error

    async def astream(self, messages):
        if self.error is not None:
            raise self.error
        for chunk in ANSWER_CHUNKS:
            yield AIMessageChunk(content=chunk)


@pytest.fixture
def model_calls(monkeypatch):
    """Replace the model factory; return the list of model ids it was asked for."""
    calls: list[str] = []

    def factory(model: str, **kwargs):
        calls.append(model)
        return _FakeChat()

    monkeypatch.setattr(llm_module, "aion_chat_openai", factory)
    return calls


@pytest.fixture
def replies(monkeypatch):
    """Capture the text the node replies with instead of sending it.

    The node calls ``thread.reply()`` itself, so the fake stands in for the SDK
    and returns what the real call returns: the posted message.
    """
    captured: list[str] = []

    async def fake_reply(self, content, **kwargs):
        captured.append(content)
        return AIMessage(content=content)

    monkeypatch.setattr(Thread, "reply", fake_reply)
    return captured


def test_model_comes_from_the_environment(model_calls):
    """The `model` configuration field selects the model."""
    asyncio.run(llm_node(_state("hi"), runtime=_runtime({"model": "configured-model"})))
    assert model_calls == ["configured-model"]


def test_model_falls_back_to_the_code_default(model_calls):
    """With no environment, or one that sets no model, the code default is used."""
    asyncio.run(llm_node(_state("hi"), runtime=_runtime(None)))
    asyncio.run(llm_node(_state("hi"), runtime=_runtime({"greeting": "Hi"})))
    assert model_calls == [DEFAULT_MODEL, DEFAULT_MODEL]


def test_answer_lands_in_state_as_one_message(model_calls, replies):
    """The streamed chunks are joined into a single AIMessage, ahead of the footer."""
    update = asyncio.run(llm_node(_state("hi"), runtime=_runtime(None)))
    assert update["messages"][0].content == "".join(ANSWER_CHUNKS)
    assert update["messages"][1].content == replies[0]


def test_missing_prompt_asks_for_one(model_calls, replies):
    """A bare `llm` explains the usage and calls no model."""
    asyncio.run(llm_node(_state(""), runtime=_runtime(None)))
    assert model_calls == []
    assert USAGE in replies[0]


def test_sdk_refusal_is_explained_in_the_reply(monkeypatch, replies):
    """An SDK error buried in a client error surfaces with the SDK's own words."""
    refusal = AionAuthenticationError("Unable to obtain an Aion API token.")
    wrapped = ConnectionError("Connection error.")
    wrapped.__cause__ = refusal
    monkeypatch.setattr(llm_module, "aion_chat_openai", lambda model, **kwargs: _FakeChat(wrapped))

    asyncio.run(llm_node(_state("hi"), runtime=_runtime(None)))

    assert str(refusal) in replies[0]


def test_model_failure_names_the_configuration_field(monkeypatch, replies):
    """Any other failure points at the `model` field instead of failing the task."""
    monkeypatch.setattr(
        llm_module, "aion_chat_openai", lambda model, **kwargs: _FakeChat(RuntimeError("boom"))
    )

    asyncio.run(llm_node(_state("hi"), runtime=_runtime({"model": "gone-model"})))

    assert "gone-model" in replies[0] and "`model`" in replies[0]
