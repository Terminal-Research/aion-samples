"""The menu, and the examples aion.yaml lists, both made from src/commands/."""

from __future__ import annotations

from src import commands
from src.tour.routing import NATIVE


def menu_lines() -> list[str]:
    """One line per command, marked when LangGraph can do it alone."""
    listed = [module.COMMAND for module in commands.COMMANDS]
    usage_width = max(len(command.usage) for command in listed)
    summary_width = max(len(command.summary) for command in listed)
    lines = []
    for command in listed:
        mark = "native ✓" if command.native else "native —" if command.no_native else ""
        lines.append(f"  {command.usage.ljust(usage_width)}  {command.summary.ljust(summary_width)}  {mark}".rstrip())
    return lines


def examples() -> list[str]:
    """Every command, then the ``native`` version of each one LangGraph can do alone."""

    def example(command, *, native: bool = False) -> str:
        words = [command.key, NATIVE] if native else [command.key]
        if command.argument_hint:
            words.append("What is the A2A protocol?")
        return " ".join(words)

    listed = [module.COMMAND for module in commands.COMMANDS]
    return [example(command) for command in listed] + [
        example(command, native=True) for command in listed if command.native
    ]
