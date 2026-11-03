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
from aion.core.exceptions import TaskFailedError
from aion.core.runtime import AionRuntimeContext
from google.adk.events import Event
from google.genai import types

from src.commands import llm as llm_module
from src.commands.llm import USAGE
from src.commands.llm import with_sdk as llm_handler

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


def _failure(error: BaseException, model: str = "some-model") -> str:
    """Run the handler against an agent that raises ``error``; return the task's failure reason."""
    _FakeAgent.error = error
    with pytest.raises(TaskFailedError) as failure:
        asyncio.run(_collect(_ctx({"model": model}), "hi"))
    return str(failure.value)


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
    """Capture the text of every message the handler sends instead of sending it.

    The handler calls ``thread.reply()`` itself, so the fake stands in for the
    SDK call rather than for a helper around it. Everything this handler sends
    through ``Thread`` is a message — a hint or the footer beside the streamed
    answer — and the fake checks that too.
    """
    captured: list[str] = []

    async def fake_reply(self, content, **kwargs):
        assert isinstance(content, str), f"a {type(content).__name__} was sent, not a message"
        captured.append(content)

    monkeypatch.setattr(Thread, "reply", fake_reply)
    return captured


def test_model_comes_from_the_environment(model_calls):
    """The `model` configuration field selects the model."""
    asyncio.run(_collect(_ctx({"model": "configured-model"}), "hi"))
    assert model_calls == ["configured-model"]


def test_no_model_means_no_call(model_calls, replies):
    """There is no default model: without one a message says how to set it."""
    asyncio.run(_collect(_ctx(None), "hi"))
    asyncio.run(_collect(_ctx({"greeting": "Hi"}), "hi"))
    assert model_calls == []
    assert "no environment" in replies[0]
    assert "Set the `model` field" in replies[1]


def test_agent_events_are_passed_through(model_calls, replies):
    """The LlmAgent's events reach the caller untouched; the footer follows as a message."""
    events = asyncio.run(_collect(_ctx({"model": "some-model"}), "hi"))
    assert [event.content.parts[0].text for event in events] == [ANSWER]
    assert len(replies) == 1 and "Answered by `some-model`" in replies[0]


def test_missing_prompt_asks_for_one(model_calls, replies):
    """A bare `llm` explains the usage in a message and builds no agent."""
    events = asyncio.run(_collect(_ctx(None), "   "))
    assert events == []
    assert model_calls == []
    assert USAGE in replies[0]


def test_sdk_refusal_fails_the_task_in_the_sdk_words(model_calls, replies):
    """An SDK error buried in a client error becomes the reason, in the SDK's own words."""
    refusal = AionAuthenticationError("Unable to obtain an Aion API token.")
    wrapped = ConnectionError("Connection error.")
    wrapped.__cause__ = refusal

    reason = _failure(wrapped)

    assert str(refusal) in reason
    assert replies == []


def test_model_failure_names_the_configuration_field(model_calls, replies):
    """Any other failure fails the task with a reason that points at the `model` field."""
    reason = _failure(RuntimeError("boom"), model="gone-model")

    assert "gone-model" in reason and "`model`" in reason
    assert replies == []


class _ServiceError(Exception):
    """Shaped like LiteLLM's error: the service's message, and its code when known."""

    def __init__(self, message: str, code: str | None):
        super().__init__(message)
        self.message = message
        self.code = code


def test_service_refusal_is_quoted_with_advice_for_its_code(model_calls, replies):
    """The service's own words reach the reason, and the advice follows its code."""
    error = _ServiceError("AgentIdentity d-1 lacks model.execute on Organization o-1.", "model_authorization_denied")

    reason = _failure(error)

    assert error.message in reason
    assert llm_module.ADVICE["model_authorization_denied"] in reason
    assert "Resources > Models" not in reason


def test_unknown_code_gets_every_likely_cause(model_calls, replies):
    """Without a known code the reason still names both fixes and the error table."""
    error = _ServiceError("litellm.APIError: Something new went wrong.", None)

    reason = _failure(error)

    assert error.message in reason
    assert "`model.execute`" in reason and "`model`" in reason
    assert llm_module.MODEL_SERVICE_DOCS in reason
