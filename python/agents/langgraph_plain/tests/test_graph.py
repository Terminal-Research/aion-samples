"""The graph, invoked directly — no server, no SDK."""

from langchain_core.messages import AIMessage, HumanMessage

from src.graph import create_graph


def _last_reply(messages: list) -> str:
    result = create_graph().compile().invoke({"messages": messages})
    reply = result["messages"][-1]
    assert isinstance(reply, AIMessage)
    return reply.content


def test_reply_describes_the_message():
    """The reply quotes the message and counts its words."""
    assert 'You said 2 word(s): "hello world"' in _last_reply([HumanMessage("hello world")])


def test_reply_counts_the_turns():
    """The turn number follows the user messages accumulated in state."""
    history = [HumanMessage("one"), AIMessage("reply"), HumanMessage("two")]
    assert "message 2 in this conversation" in _last_reply(history)


def test_content_blocks_are_read_as_text():
    """The server delivers content as blocks; the graph reads them like a string."""
    blocks = [{"type": "text", "text": "hello"}, {"type": "text", "text": " there"}]
    assert '"hello there"' in _last_reply([HumanMessage(content=blocks)])
