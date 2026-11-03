"""Fixtures shared by the node tests."""

import pytest

from tests.support import Reply, capture_replies, capture_thoughts


@pytest.fixture
def replies(monkeypatch) -> list[Reply]:
    """Every ``thread.reply()`` and ``thread.post()`` call a node makes, captured instead of sent."""
    return capture_replies(monkeypatch)


@pytest.fixture
def thoughts(monkeypatch) -> list[str]:
    """Every ``thread.thinking()`` call a node makes, captured instead of sent."""
    return capture_thoughts(monkeypatch)
