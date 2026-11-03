"""The graph state: the conversation, plus the keys the tour keeps."""

from typing import Annotated, Optional, TypedDict

from aion.langgraph.authoring import A2AOutboxField
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class TourState(TypedDict):
    """State carried between the tour's nodes.

    Attributes:
        messages: The conversation, kept across turns that share a context id:
            the user's messages and every message the agent sent. An answer
            sent as an artifact is the task's result, not a message, so it is
            not here and a later model call does not see it.
        command: The key of the command the turn asked for, or None when the
            input matched nothing.
        native: Whether the turn asked for ``<command> native``.
        argument: The text after the keyword, for a command that takes one.
        input_text: The raw inbound text, which the menu quotes when nothing matched.
        a2a_outbox: An A2A Task or Message the agent built itself. On
            ``A2AOutboxField`` LangGraph does not checkpoint it: it answers the
            turn that wrote it and is gone from the next one.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    command: Optional[str]
    native: Optional[bool]
    argument: Optional[str]
    input_text: Optional[str]
    a2a_outbox: A2AOutboxField
