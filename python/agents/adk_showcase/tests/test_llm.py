"""The `llm` handler — model choice and failure handling, with the model faked."""

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
from aion.adk.authoring.invocation import Thread
from aion.core.runtime import AionRuntimeContext
from google.adk.events import Event
from google.genai import types

from src.handlers import llm as llm_module
from src.handlers.llm import DEFAULT_MODEL, USAGE, llm_handler

ANSWER = "Hello, world"


def _ctx(configuration: dict[str, str] | None = None) -> SimpleNamespace:
    """Build an invocation context whose runtime carries an environment, or none."""
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
    return SimpleNamespace(
        aion_runtime_context=AionRuntimeContext(distribution_extension_payload=payload)
    )


class _FakeAgent:
    """Stands in for ``LlmAgent``: yields one final event, or fails."""

    error: BaseException | None = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def run_async(self, ctx):
        if self.error is not None:
            raise self.error
        yield Event(
            author="llm",
            content=types.Content(role="model", parts=[types.Part(text=ANSWER)]),
            partial=False,
        )


async def _collect(ctx, prompt: str) -> list[Event]:
    return [event async for event in llm_handler(ctx, prompt)]


@pytest.fixture
def model_calls(monkeypatch):
    """Fake the model factory and the agent; return the model ids asked for."""
    calls: list[str] = []

    def factory(model: str, **kwargs):
        calls.append(model)
        return f"lite-llm:{model}"

    monkeypatch.setattr(llm_module, "aion_lite_llm", factory)
    monkeypatch.setattr(llm_module, "LlmAgent", _FakeAgent)
    _FakeAgent.error = None
    return calls


@pytest.fixture
def replies(monkeypatch):
    """Capture the text the handler replies with instead of sending it.

    The handler calls ``thread.reply()`` itself, so the fake stands in for the
    SDK call rather than for a helper around it.
    """
    captured: list[str] = []

    async def fake_reply(self, content, **kwargs):
        captured.append(content)

    monkeypatch.setattr(Thread, "reply", fake_reply)
    return captured


def test_model_comes_from_the_environment(model_calls):
    """The `model` configuration field selects the model."""
    asyncio.run(_collect(_ctx({"model": "configured-model"}), "hi"))
    assert model_calls == ["configured-model"]


def test_model_falls_back_to_the_code_default(model_calls):
    """With no environment, or one that sets no model, the code default is used."""
    asyncio.run(_collect(_ctx(None), "hi"))
    asyncio.run(_collect(_ctx({"greeting": "Hi"}), "hi"))
    assert model_calls == [DEFAULT_MODEL, DEFAULT_MODEL]


def test_agent_events_are_passed_through(model_calls):
    """The LlmAgent's events reach the caller untouched."""
    events = asyncio.run(_collect(_ctx(None), "hi"))
    assert [event.content.parts[0].text for event in events] == [ANSWER]


def test_missing_prompt_asks_for_one(model_calls, replies):
    """A bare `llm` explains the usage and builds no agent."""
    events = asyncio.run(_collect(_ctx(None), "   "))
    assert events == []
    assert model_calls == []
    assert USAGE in replies[0]


def test_sdk_refusal_is_explained_in_the_reply(model_calls, replies):
    """An SDK error buried in a client error surfaces with the SDK's own words."""
    refusal = AionAuthenticationError("Unable to obtain an Aion API token.")
    wrapped = ConnectionError("Connection error.")
    wrapped.__cause__ = refusal
    _FakeAgent.error = wrapped

    events = asyncio.run(_collect(_ctx(None), "hi"))

    assert events == []
    assert str(refusal) in replies[0]


def test_model_failure_names_the_configuration_field(model_calls, replies):
    """Any other failure points at the `model` field instead of failing the task."""
    _FakeAgent.error = RuntimeError("boom")

    events = asyncio.run(_collect(_ctx({"model": "gone-model"}), "hi"))

    assert events == []
    assert "gone-model" in replies[0] and "`model`" in replies[0]
