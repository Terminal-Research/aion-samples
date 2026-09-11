"""A LangGraph graph with nothing Aion-specific in it.

Nothing here imports from ``aion``. The SDK puts the inbound message into
``state["messages"]`` as a ``HumanMessage``, keeps the state per conversation,
and turns the ``AIMessage`` a node returns into the reply.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph


def reply(state: MessagesState) -> dict:
    """Describe the latest user message and count the turns so far."""
    turns = [message for message in state["messages"] if isinstance(message, HumanMessage)]

    # The server delivers the inbound text as a list of content blocks; a
    # message built in code carries a plain string. Both are valid LangChain
    # content, so a node that reads text handles the two.
    content = turns[-1].content
    if isinstance(content, str):
        text = content.strip()
    else:
        text = "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()

    return {
        "messages": [
            AIMessage(
                content=f'You said {len(text.split())} word(s): "{text}". '
                f"That was message {len(turns)} in this conversation."
            )
        ]
    }


def create_graph() -> StateGraph:
    """Build the graph; the Aion server compiles and serves it."""
    workflow = StateGraph(MessagesState)
    workflow.add_node("reply", reply)
    workflow.add_edge(START, "reply")
    workflow.add_edge("reply", END)
    return workflow
