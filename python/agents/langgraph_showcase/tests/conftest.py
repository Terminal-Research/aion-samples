"""Fixtures shared by the node tests."""

import pytest

from tests.support import Reply, capture_replies


@pytest.fixture
def replies(monkeypatch) -> list[Reply]:
    """Every ``thread.reply()`` call a node makes, captured instead of sent."""
    return capture_replies(monkeypatch)
