"""What the tour knows about a command."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """One command of the tour; it lives in ``src/commands/<key>.py``.

    Attributes:
        key: The keyword the user types.
        summary: One line for the menu.
        api: The SDK call the command shows; its replies end by naming it.
        native: How ADK does it alone, when it can.
        no_native: Why ADK alone cannot, when it cannot.
        argument_hint: The name of the text the command takes after its keyword.
    """

    key: str
    summary: str
    api: str
    native: str | None = None
    no_native: str | None = None
    argument_hint: str | None = None

    @property
    def source(self) -> str:
        """The file the command is written in."""
        return f"src/commands/{self.key}.py"

    @property
    def footer(self) -> str:
        """The end of a reply made with the SDK: the call, and the file it is in."""
        return f"\n\n↳ {self.api} · {self.source}"

    @property
    def usage(self) -> str:
        """The command as the menu spells it, argument included."""
        return f"{self.key} {{{self.argument_hint}}}" if self.argument_hint else self.key
