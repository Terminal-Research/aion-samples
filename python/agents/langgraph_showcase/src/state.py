"""Graph state for the showcase agent."""

from typing import Annotated, Optional, TypedDict

from aion.langgraph.authoring import A2AOutboxField
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State carried between the showcase agent's nodes.

    Attributes:
        messages: Conversation history, accumulated across turns that share a
            context id: the user's messages, and the messages the agent keeps
            in the conversation — explanations, the message `ask` sends
            before it waits, the message `post` sends, and the streamed
            answers of `stream`, `sections` and `llm`. Answers sent as text
            artifacts are the task's result, not messages, so they are not in
            it and a later model call does not see them. The ``context``
            command reports its length.
        command: Canonical key of the resolved command, or None when the input
            matched nothing.
        input_text: Raw inbound text, kept so the menu can quote unknown input.
        argument: Free-form text typed after the keyword, for commands that
            accept one. Empty for every other command.
        a2a_outbox: Explicit A2A response, set by the task and message
            commands. ``A2AOutboxField`` keeps it out of the checkpoint: it
            answers the turn that wrote it and is gone from the next one.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    command: Optional[str]
    input_text: Optional[str]
    argument: Optional[str]
    a2a_outbox: A2AOutboxField
