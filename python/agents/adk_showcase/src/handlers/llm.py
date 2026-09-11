"""A model answers, through the platform's model service."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.adk.authoring.models import aion_lite_llm
from aion.api.exceptions import AionAuthenticationError
from google.adk.agents import LlmAgent
from google.adk.events import Event

from src.replies import with_footer

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-nano"
"""Model used when the turn carries no environment. Keep it equal to the
``default`` of the ``model`` field in aion.yaml: the control plane applies that
one, this one covers a direct local call."""

INSTRUCTION = (
    "You are the `llm` command of a showcase agent on the Aion platform. The "
    "user's message starts with the keyword `llm`, which routed it to you and "
    "is not part of the question. Answer briefly, in plain text."
)

USAGE = "Send a question after the keyword, e.g. `llm What is the A2A protocol?`."


async def llm_handler(ctx: AionInvocationContext, prompt: str) -> AsyncGenerator[Event, None]:
    """Hand the turn to an ``LlmAgent`` whose model is the platform's.

    ``aion_lite_llm()`` returns ADK's own ``LiteLlm`` pointed at the platform's
    model service, so the agent that answers is an ordinary ``LlmAgent`` with
    the session as its conversation history. Its events are yielded as they
    are: the partial ones stream the tokens, the final one is the durable
    reply. Nothing about the answer goes through ``Thread``; only the closing
    footer is sent explicitly.

    The model service runs work for a principal, which arrives with an
    invocation the platform delivers. A direct local call carries none, so
    the SDK refuses the call before sending it. Every failure is reported in
    the reply rather than raised, because a broken model is not a broken task.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    if not prompt.strip():
        await thread.reply(with_footer("llm", USAGE))
        return

    environment = ctx.aion_runtime_context.get_environment()
    model = (environment.get_configuration_variable("model") if environment else None) or DEFAULT_MODEL
    agent = LlmAgent(name="llm", model=aion_lite_llm(model), instruction=INSTRUCTION)

    try:
        async for event in agent.run_async(ctx):
            yield event
    except Exception as exc:
        refusal = _refusal(exc)
        # A refusal is expected and self-explanatory; anything else keeps its traceback.
        logger.warning("Model %s did not answer: %s", model, refusal or exc, exc_info=refusal is None)
        await thread.reply(with_footer("llm", *_explain(model, exc, refusal)))
        return

    await thread.reply(
        with_footer(
            "llm",
            f"That answer came from `{model}` and reached you without `thread.reply()`: "
            "an `LlmAgent` produced it, its partial events streamed the tokens and its "
            "final event became the durable reply. Only this footer was sent "
            "explicitly.",
            "",
            "The model is the `model` field of this environment's configuration — "
            "change it there to switch models without touching the code.",
        )
    )


def _refusal(exc: BaseException) -> AionAuthenticationError | None:
    """Return the SDK error behind a failed call, if that is what it was.

    A refusal by the SDK — no credentials, no principal — is an
    ``AionAuthenticationError`` (the principal error is a subclass). It arrives
    wrapped in the client library's connection error, with the SDK's own
    explanation as the cause.
    """
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, AionAuthenticationError):
            return cause
        cause = cause.__cause__
    return None


def _explain(model: str, exc: BaseException, refusal: AionAuthenticationError | None) -> list[str]:
    """Turn a failed model call into reply lines.

    The SDK's own explanation is the useful part of a refusal, so it is shown
    verbatim. Anything else points at the configuration field to change.
    """
    if refusal is not None:
        return ["No model call was made.", "", str(refusal)]
    return [
        f"Model `{model}` did not answer ({type(exc).__name__}).",
        "",
        "Set the `model` field of this environment's configuration to a model "
        "from the catalog (Resources > Models) and send `llm` again.",
    ]
