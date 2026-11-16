"""The `llm` command — its sub-agent, model choice and failure handling, with the model faked."""

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
from aion.adk.authoring.models import CHOSEN_PER_REQUEST
from aion.core.exceptions import TaskFailedError
from aion.core.runtime import AionRuntimeContext
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.genai import types

from src.agent import create_agent
from src.commands import llm as llm_module
from src.commands.llm import USAGE, configured_model
from src.commands.llm import with_sdk as llm_handler

ANSWER = "Hello, world"


def _runtime(configuration: dict[str, str] | None = None) -> AionRuntimeContext:
    """A runtime context whose environment has ``configuration``, or no environment."""
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
    return AionRuntimeContext(distribution_extension_payload=payload)


class _FakeAgent:
    """Stands in for the `llm` sub-agent: yields one final event, or fails."""

    def __init__(self):
        self.error: BaseException | None = None
        self.runs = 0

    async def run_async(self, ctx):
        self.runs += 1
        if self.error is not None:
            raise self.error
        yield Event(
            author="llm",
            content=types.Content(role="model", parts=[types.Part(text=ANSWER)]),
            partial=False,
        )


def _ctx(sub_agent: _FakeAgent, configuration: dict[str, str] | None = None) -> SimpleNamespace:
    """The showcase's invocation context: its runtime, and its agent with the `llm` sub-agent."""
    return SimpleNamespace(
        aion_runtime_context=_runtime(configuration),
        agent=SimpleNamespace(find_sub_agent={"llm": sub_agent}.get),
    )


async def _collect(ctx, prompt: str) -> list[Event]:
    return [event async for event in llm_handler(ctx, prompt)]


@pytest.fixture
def sub_agent() -> _FakeAgent:
    return _FakeAgent()


def _failure(sub_agent: _FakeAgent, error: BaseException, model: str = "some-model") -> str:
    """Run the handler against a sub-agent that raises ``error``; return the task's failure reason."""
    sub_agent.error = error
    with pytest.raises(TaskFailedError) as failure:
        asyncio.run(_collect(_ctx(sub_agent, {"model": model}), "hi"))
    return str(failure.value)


@pytest.fixture
def replies(monkeypatch):
    """Capture the text of what the handler sends instead of sending it.

    A hint (no prompt, no model) is the turn's answer, a text artifact; the
    footer beside a model's answer is a message. Each is captured as
    ``(kind, text)``.
    """
    captured: list[tuple[str, str]] = []

    async def fake_reply(self, content, **kwargs):
        if isinstance(content, str):
            captured.append(("message", content))
        else:
            captured.append(("artifact", content.parts[0].text))

    monkeypatch.setattr(Thread, "reply", fake_reply)
    return captured


def test_llm_is_a_declared_sub_agent():
    """The showcase declares the `llm` LlmAgent in `sub_agents`; its model is chosen per request."""
    showcase = create_agent()
    agent = showcase.find_sub_agent("llm")

    assert isinstance(agent, LlmAgent)
    assert agent.parent_agent is showcase
    assert agent.model.model == CHOSEN_PER_REQUEST


def test_model_comes_from_the_environment():
    """The `model` configuration field is the model; without it, or an environment, there is none."""
    assert configured_model(_runtime({"model": "configured-model"})) == "configured-model"
    assert configured_model(_runtime({"greeting": "Hi"})) is None
    assert configured_model(_runtime(None)) is None
    assert configured_model(None) is None


def test_no_model_means_no_call(sub_agent, replies):
    """There is no default model: without one a text artifact says how to set it."""
    asyncio.run(_collect(_ctx(sub_agent, None), "hi"))
    asyncio.run(_collect(_ctx(sub_agent, {"greeting": "Hi"}), "hi"))
    assert sub_agent.runs == 0
    assert replies[0][0] == replies[1][0] == "artifact"
    assert "no environment" in replies[0][1]
    assert "Set the `model` field" in replies[1][1]


def test_agent_events_are_passed_through(sub_agent, replies):
    """The sub-agent's events reach the caller untouched; the footer follows as a message."""
    events = asyncio.run(_collect(_ctx(sub_agent, {"model": "some-model"}), "hi"))
    assert [event.content.parts[0].text for event in events] == [ANSWER]
    assert len(replies) == 1 and replies[0][0] == "message" and "Answered by `some-model`" in replies[0][1]


def test_missing_prompt_asks_for_one(sub_agent, replies):
    """A bare `llm` explains the usage in a text artifact and runs no agent."""
    events = asyncio.run(_collect(_ctx(sub_agent, None), "   "))
    assert events == []
    assert sub_agent.runs == 0
    assert replies[0][0] == "artifact" and USAGE in replies[0][1]


def test_sdk_refusal_fails_the_task_in_the_sdk_words(sub_agent, replies):
    """An SDK error buried in a client error becomes the reason, in the SDK's own words."""
    refusal = AionAuthenticationError("Unable to obtain an Aion API token.")
    wrapped = ConnectionError("Connection error.")
    wrapped.__cause__ = refusal

    reason = _failure(sub_agent, wrapped)

    assert str(refusal) in reason
    assert replies == []


def test_model_failure_names_the_configuration_field(sub_agent, replies):
    """Any other failure fails the task with a reason that points at the `model` field."""
    reason = _failure(sub_agent, RuntimeError("boom"), model="gone-model")

    assert "gone-model" in reason and "`model`" in reason
    assert replies == []


class _ServiceError(Exception):
    """Shaped like LiteLLM's error: the service's message, and its code when known."""

    def __init__(self, message: str, code: str | None):
        super().__init__(message)
        self.message = message
        self.code = code


def test_service_refusal_is_quoted_with_advice_for_its_code(sub_agent, replies):
    """The service's own words reach the reason, and the advice follows its code."""
    error = _ServiceError("AgentIdentity d-1 lacks model.execute on Organization o-1.", "model_authorization_denied")

    reason = _failure(sub_agent, error)

    assert error.message in reason
    assert llm_module.ADVICE["model_authorization_denied"] in reason
    assert "Resources > Models" not in reason


def test_unknown_code_gets_every_likely_cause(sub_agent, replies):
    """Without a known code the reason still names both fixes and the error table."""
    error = _ServiceError("litellm.APIError: Something new went wrong.", None)

    reason = _failure(sub_agent, error)

    assert error.message in reason
    assert "`model.execute`" in reason and "`model`" in reason
    assert llm_module.MODEL_SERVICE_DOCS in reason
