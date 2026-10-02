"""The answer that resumes `ask`, in every shape the resume payload takes."""

from langchain_core.messages import HumanMessage

from src.nodes.hitl import _resumed_text


def test_plain_string_is_taken_as_is():
    assert _resumed_text("  staging  ") == "staging"


def test_message_with_string_content():
    assert _resumed_text({"messages": [HumanMessage("staging")]}) == "staging"


def test_message_with_content_blocks_is_what_the_server_sends():
    """The server resumes with content blocks, not a string — read them as text."""
    blocks = [{"type": "text", "text": "staging"}, {"type": "text", "text": " please"}]
    assert _resumed_text({"messages": [HumanMessage(content=blocks)]}) == "staging please"


def test_anything_else_is_no_answer():
    assert _resumed_text(None) == ""
    assert _resumed_text({"messages": []}) == ""
