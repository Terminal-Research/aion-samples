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

    The model is the ``model`` field of the environment's configuration, with
    no default in the code or in aion.yaml: whoever deploys the agent picks
    one, and until then the turn is answered with how to set it.

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
    model = environment.get_configuration_variable("model") if environment else None
    if not model:
        await thread.reply(with_footer("llm", *_no_model(environment is not None)))
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
        await thread.reply(with_footer("llm", *_explain(model, exc, refusal)))
        return

    await thread.reply(
        with_footer("llm", f"Answered by `{model}`, the `model` field of this environment's configuration.")
    )


def _no_model(has_environment: bool) -> list[str]:
    """Reply lines for a turn that selects no model; no call is made for it."""
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
    """Turn a failed model call into reply lines.

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
