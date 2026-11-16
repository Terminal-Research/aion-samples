"""Every command of the tour, one file each, in the order the menu lists them.

A file holds one command: ``COMMAND`` says what it is, ``with_sdk`` does it
with the Aion SDK, and ``with_langgraph``, when LangGraph can, does it alone.
"""

from src.commands import (
    artifact,
    ask,
    attachment,
    card,
    composite,
    config,
    context,
    data,
    fail,
    file,
    help,
    http,
    llm,
    message,
    metadata,
    post,
    progress,
    react,
    sections,
    stream,
    task,
    thinking,
)

COMMANDS = (
    help, stream, sections, llm, thinking, card, artifact, file, data, composite, ask,
    react, post, metadata, progress, task, message, fail, context, attachment, config, http,
)

BY_KEY = {module.COMMAND.key: module for module in COMMANDS}
