"""The tour's own plumbing: reading the keyword, picking the node, the menu and the footers.

An agent of your own needs none of it. Every lesson is a file in src/commands/.

    command.py   Command: the key, a summary, the SDK call, and the native way or why there is none
    routing.py   keyword (or card button) and ``native`` -> node, and the answer for
                 ``<command> native`` when LangGraph alone cannot do it
    menu.py      the menu, and the examples aion.yaml lists
    state.py     the graph state: the conversation, plus the keys the tour keeps
    standins.py  a text stream and a chat model that need no real model
"""

from src.tour.command import Command
from src.tour.standins import chat_model, stream_text
from src.tour.state import TourState

__all__ = ["Command", "TourState", "chat_model", "stream_text"]
