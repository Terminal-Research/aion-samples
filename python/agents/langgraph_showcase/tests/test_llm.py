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
from aion.core.exceptions import TaskFailedError
from aion.core.runtime import AionRuntimeContext
from langchain_core.messages import AIMessageChunk

from src.nodes import llm as llm_module
from src.nodes.llm import USAGE, llm_node
from tests.support import message_text

ANSWER_CHUNKS = ("Hello", ", ", "world")
STREAM_ID = "lc_run--stream"


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


def _failure(monkeypatch, error: BaseException, model: str = "some-model") -> str:
    """Run the node against a model that raises ``error``; return the task's failure reason."""
    monkeypatch.setattr(llm_module, "aion_chat_openai", lambda model, **kwargs: _FakeChat(error))
    with pytest.raises(TaskFailedError) as failure:
        asyncio.run(llm_node(_state("hi"), runtime=_runtime({"model": model})))
    return str(failure.value)


class _FakeChat:
    """Stands in for the chat model: streams fixed chunks or fails."""

    def __init__(self, error: BaseException | None = None):
        self.error = error

    async def astream(self, messages):
        if self.error is not None:
            raise self.error
        for chunk in ANSWER_CHUNKS:
            yield AIMessageChunk(content=chunk, id=STREAM_ID)


@pytest.fixture
def model_calls(monkeypatch):
    """Replace the model factory; return the list of model ids it was asked for."""
    calls: list[str] = []

    def factory(model: str, **kwargs):
        calls.append(model)
        return _FakeChat()

    monkeypatch.setattr(llm_module, "aion_chat_openai", factory)
    return calls


def test_model_comes_from_the_environment(model_calls):
    """The `model` configuration field selects the model."""
    asyncio.run(llm_node(_state("hi"), runtime=_runtime({"model": "configured-model"})))
    assert model_calls == ["configured-model"]


def test_no_model_means_no_call(model_calls, replies):
    """There is no default model: without one a message says how to set it."""
    first = asyncio.run(llm_node(_state("hi"), runtime=_runtime(None)))
    second = asyncio.run(llm_node(_state("hi"), runtime=_runtime({"greeting": "Hi"})))
    assert model_calls == []
    assert "no environment" in message_text(replies[0])
    assert "Set the `model` field" in message_text(replies[1])
    assert [message.content for message in first["messages"]] == [replies[0].content]
    assert [message.content for message in second["messages"]] == [replies[1].content]


def test_model_answer_is_followed_by_a_footer_message(model_calls, replies):
    """The streamed chunks become one AIMessage; the footer after them is a message."""
    update = asyncio.run(llm_node(_state("hi"), runtime=_runtime({"model": "some-model"})))
    assert len(replies) == 1
    assert "Answered by `some-model`" in message_text(replies[0])
    assert [message.content for message in update["messages"]] == [
        "".join(ANSWER_CHUNKS),
        replies[0].content,
    ]
    # Under the streamed id, so LangGraph does not send the answer a second time.
    assert update["messages"][0].id == STREAM_ID


def test_missing_prompt_asks_for_one(model_calls, replies):
    """A bare `llm` explains the usage in a message and calls no model."""
    update = asyncio.run(llm_node(_state(""), runtime=_runtime(None)))
    assert model_calls == []
    assert USAGE in message_text(replies[0])
    assert [message.content for message in update["messages"]] == [replies[0].content]


def test_sdk_refusal_fails_the_task_in_the_sdk_words(monkeypatch, replies):
    """An SDK error buried in a client error becomes the reason, in the SDK's own words."""
    refusal = AionAuthenticationError("Unable to obtain an Aion API token.")
    wrapped = ConnectionError("Connection error.")
    wrapped.__cause__ = refusal

    reason = _failure(monkeypatch, wrapped)

    assert str(refusal) in reason
    assert replies == []


def test_model_failure_names_the_configuration_field(monkeypatch, replies):
    """Any other failure fails the task with a reason that points at the `model` field."""
    reason = _failure(monkeypatch, RuntimeError("boom"), model="gone-model")

    assert "gone-model" in reason and "`model`" in reason
    assert replies == []


class _ServiceError(Exception):
    """Shaped like the OpenAI client's error: the service's message and code."""

    def __init__(self, message: str, code: str | None):
        super().__init__(message)
        self.message = message
        self.code = code


def test_service_refusal_is_quoted_with_advice_for_its_code(monkeypatch, replies):
    """The service's own words reach the reason, and the advice follows its code."""
    error = _ServiceError("AgentIdentity d-1 lacks model.execute on Organization o-1.", "model_authorization_denied")

    reason = _failure(monkeypatch, error)

    assert error.message in reason
    assert llm_module.ADVICE["model_authorization_denied"] in reason
    assert "Resources > Models" not in reason


def test_unknown_code_gets_every_likely_cause(monkeypatch, replies):
    """A code the sample does not know still names both fixes and the error table."""
    error = _ServiceError("Something new went wrong.", "something_new")

    reason = _failure(monkeypatch, error)

    assert error.message in reason
    assert "`model.execute`" in reason and "`model`" in reason
    assert llm_module.MODEL_SERVICE_DOCS in reason
