"""The tour's own plumbing: reading the keyword, picking the handler, the menu and the footers.

An agent of your own needs none of it. Every lesson is a file in src/commands/.

    command.py   Command: the key, a summary, the SDK call, and the native way or why there is none
    routing.py   the keyword (or card button) and ``native`` of a turn, and the answer for
                 ``<command> native`` when ADK alone cannot do it
    menu.py      the menu, and the examples aion.yaml lists
    standins.py  a text stream that needs no real model
"""

from src.tour.command import Command
from src.tour.standins import stream_text

__all__ = ["Command", "stream_text"]
