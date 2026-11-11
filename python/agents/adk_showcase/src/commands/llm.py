"""`llm`: a model answers your prompt through the platform's model service.

The answer is an ordinary ``LlmAgent``'s events; the SDK supplies only the
model, ``aion_lite_llm()``. So ``llm native`` runs this command as it is.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from aion.adk.authoring.invocation import AionInvocationContext, Thread
from aion.adk.authoring.models import aion_lite_llm
from aion.api.exceptions import AionAuthenticationError
from aion.core.a2a import text_artifact
from aion.core.exceptions import TaskFailedError
from google.adk.agents import LlmAgent
from google.adk.events import Event

from src.tour import Command

logger = logging.getLogger(__name__)

COMMAND = Command(
    key="llm",
    summary="A model answers your prompt, and reads a file you attach, through the platform's model service",
    api="LlmAgent(model=aion_lite_llm(model))",
    native="the events of an LlmAgent, which `llm` already yields; the SDK supplies only the model",
    argument_hint="prompt",
)

INSTRUCTION = (
    "You are the `llm` command of a showcase agent on the Aion platform. The "
    "user's message starts with the keyword `llm`, which routed it to you and "
    "is not part of the question. Answer briefly, in plain text. A file "
    "attached to the message is part of the question."
)

USAGE = (
    "Send a question after the keyword, e.g. `llm What is the A2A protocol?`. "
    "Attach a file and the model reads it."
)


async def with_sdk(ctx: AionInvocationContext, prompt: str) -> AsyncGenerator[Event, None]:
    """Hand the turn to an ``LlmAgent`` whose model is the platform's, and let its answer stream.

    The agent's partial events stream the tokens in ``aion:stream-delta``. The
    model is the ``model`` field of the environment's configuration, and the
    model service answers only a turn the platform delivered. A refused or
    failed call ends the task as failed, with the explanation as its reason.

    The ``LlmAgent`` reads the user's message as it arrived, so a file attached
    to it reaches the model with no code here. On a deployment that stores
    files the message holds the file's address; the model the SDK builds
    sends the file's content in its place.
    """
    thread = Thread.from_context(ctx.aion_runtime_context)

    if not prompt.strip():
        await thread.reply(text_artifact(USAGE + COMMAND.footer))
        return

    environment = ctx.aion_runtime_context.get_environment()
    model = environment.get_configuration_variable("model") if environment else None
    if not model:
        await thread.reply(text_artifact("\n".join(_no_model(environment is not None)) + COMMAND.footer))
        return
    agent = LlmAgent(name="llm", model=aion_lite_llm(model), instruction=INSTRUCTION)

    try:
        async for event in agent.run_async(ctx):
            yield event
    except Exception as exc:
        refusal = _refusal(exc)
        # A refusal is expected and self-explanatory; anything else keeps its traceback.
        logger.warning(
            "Model %s did not answer (code %s): %s",
            model,
            getattr(exc, "code", None),
            refusal or exc,
            exc_info=refusal is None,
        )
        raise TaskFailedError("\n".join(_explain(model, exc, refusal))) from exc

    files = thread.message.files if thread.message is not None else []
    read = f" It was sent {len(files)} attached file(s), by their content." if files else ""
    await thread.reply(
        f"Answered by `{model}`, the `model` field of this environment's configuration.{read}" + COMMAND.footer
    )


def _no_model(has_environment: bool) -> list[str]:
    """Answer lines for a turn that selects no model; no call is made for it."""
    if not has_environment:
        return [
            "No model call was made: this turn carries no environment, so no model is selected.",
            "",
            "`llm` uses the `model` field of the environment's configuration, which arrives "
            "with a turn the platform delivers.",
        ]
    return [
        "No model call was made: this environment has no model selected.",
        "",
        "Set the `model` field of its configuration to a model from Resources > Models, "
        "then send `llm` again.",
    ]


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


MODEL_SERVICE_DOCS = "https://docs.aion.to/docs/resources/model-service#troubleshoot-a-request"
"""Where the model service documents its error codes."""

ADVICE = {
    "model_not_found": (
        "Copy the exact model ID from Resources > Models into the `model` field of this "
        "environment's configuration, then send `llm` again."
    ),
    "model_not_supported": (
        "Set the `model` field of this environment's configuration to a text-producing "
        "model from Resources > Models, then send `llm` again."
    ),
    "model_authorization_denied": (
        "The call ran as this environment's Daemon Identity, and its role does not include "
        "`model.execute` in the organization. Give the Daemon Identity a role that covers "
        "models — of the agent roles, Organization Agent does — then send `llm` again. "
        "A personal API key acts as its user, who needs `model.execute` instead."
    ),
    "insufficient_credits": "The organization is out of Aion credits; review its credit balance.",
    "billing_organization_required": (
        "The call is not tied to an active organization; deploy the agent in one, or use "
        "runtime credentials that belong to one."
    ),
    "credit_policy_suspended": (
        "The organization's credit policy is suspended; ask an organization administrator to "
        "review it."
    ),
}
"""What to do about each error code the model service documents."""


def _explain(model: str, exc: BaseException, refusal: AionAuthenticationError | None) -> list[str]:
    """Turn a failed model call into the lines of the task's failure reason.

    Whoever refused the call explains it best, so its words are shown verbatim:
    the SDK's, when it refused before sending, or the model service's. The
    service also sends a stable error ``code``; the advice is chosen by that
    code, never by the wording of the message, which may change.
    """
    if refusal is not None:
        return ["No model call was made.", "", str(refusal)]

    # LiteLLM's errors carry the service's ``message``, and a ``code`` when the
    # service's error body reached them; read both by name so any other failure
    # falls through to the generic advice.
    said = getattr(exc, "message", None)
    code = getattr(exc, "code", None)
    lines = [f"Model `{model}` did not answer ({type(exc).__name__})."]
    if isinstance(said, str) and said.strip():
        lines += ["", f"The model service said: {said.strip()}"]
    advice = ADVICE.get(code) if isinstance(code, str) else None
    if advice is not None:
        return lines + ["", advice]
    return lines + [
        "",
        "If the model is not in the catalog, set the `model` field of this environment's "
        "configuration to one from Resources > Models. If a permission is missing, the "
        "environment's Daemon Identity needs a role with `model.execute`. Every error code "
        f"is explained at {MODEL_SERVICE_DOCS}",
    ]
