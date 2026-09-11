"""A model answers, through the platform's model service."""

from __future__ import annotations

import logging

from aion.api.exceptions import AionAuthenticationError
from aion.core.runtime import AionRuntimeContext
from aion.langgraph.authoring.invocation import Thread
from aion.langgraph.authoring.models import aion_chat_openai
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from src.replies import with_footer
from src.state import AgentState

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-nano"
"""Model used when the turn carries no environment. Keep it equal to the
``default`` of the ``model`` field in aion.yaml: the control plane applies that
one, this one covers a direct local call."""

SYSTEM_PROMPT = (
    "You are the `llm` command of a showcase agent on the Aion platform. "
    "Answer the question briefly, in plain text."
)

USAGE = "Send a question after the keyword, e.g. `llm What is the A2A protocol?`."


async def llm_node(state: AgentState, *, runtime: Runtime[AionRuntimeContext]) -> dict:
    """Send the prompt to a model and let its answer stream natively.

    ``aion_chat_openai()`` returns a regular LangChain ``ChatOpenAI`` pointed
    at the platform's model service, so this node calls it the way any
    LangGraph node calls a model. Nothing about the answer goes through
    ``Thread``: the server streams LangGraph's ``messages`` mode, so the
    chunks from ``astream()`` reach the client as they arrive, and the
    ``AIMessage`` returned into state becomes the durable reply. Only the
    closing footer is sent explicitly.

    The model service runs work for a principal, which arrives with an
    invocation the platform delivers. A direct local call carries none, so
    the SDK refuses the call before sending it. Every failure is reported in
    the reply rather than raised, because a broken model is not a broken task.
    """
    thread = Thread.from_context(runtime.context)

    prompt = (state.get("argument") or "").strip()
    if not prompt:
        reply = await thread.reply(with_footer("llm", USAGE))
        return {"messages": [reply]}

    environment = runtime.context.get_environment()
    model = (environment.get_configuration_variable("model") if environment else None) or DEFAULT_MODEL
    chat = aion_chat_openai(model)

    try:
        chunks = [
            chunk
            async for chunk in chat.astream([SystemMessage(SYSTEM_PROMPT), HumanMessage(prompt)])
        ]
    except Exception as exc:
        refusal = _refusal(exc)
        # A refusal is expected and self-explanatory; anything else keeps its traceback.
        logger.warning("Model %s did not answer: %s", model, refusal or exc, exc_info=refusal is None)
        reply = await thread.reply(with_footer("llm", *_explain(model, exc, refusal)))
        return {"messages": [reply]}

    answer = "".join(_text(chunk.content) for chunk in chunks)
    footer_reply = await thread.reply(
        with_footer(
            "llm",
            f"That answer came from `{model}` and reached you without `thread.reply()`: "
            "the tokens streamed straight out of the model call, and the message "
            "returned into state became the durable reply. Only this footer was "
            "sent explicitly.",
            "",
            "The model is the `model` field of this environment's configuration — "
            "change it there to switch models without touching the code.",
        )
    )
    return {"messages": [AIMessage(content=answer), footer_reply]}


def _text(content: object) -> str:
    """Return the text of a chunk's content, whether a string or content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )
    return ""


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
