"""Graph state for the showcase agent."""

from typing import Annotated, Optional, TypedDict

from aion.core.a2a import A2AOutbox
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State carried between the showcase agent's nodes.

    Attributes:
        messages: Conversation history, accumulated across turns that share a
            context id. Every node returns the message it posted into this
            list, and the ``context`` command reports its length.
        command: Canonical key of the resolved command, or None when the input
            matched nothing.
        input_text: Raw inbound text, kept so the menu can quote unknown input.
        argument: Free-form text typed after the keyword, for commands that
            accept one. Empty for every other command.
        a2a_outbox: Explicit A2A response, set by the task/message/fail commands.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    command: Optional[str]
    input_text: Optional[str]
    argument: Optional[str]
    a2a_outbox: Optional[A2AOutbox]
