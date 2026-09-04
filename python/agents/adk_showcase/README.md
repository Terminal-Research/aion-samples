# ADK Showcase

A guided tour of what an agent can do on the Aion platform, built with Google ADK.

Send it a keyword and it performs one demonstration, then tells you which SDK call
produced what you just saw and which file it lives in. Every reply is text the agent
already knows, streamed in chunks the way a model streams tokens — so what you are
looking at is platform behaviour, not model output. Replies are plain text; `card` is
the one command that sends a rich card, and `stream` the one that paces itself —
everywhere else the chunks go out back to back.

## Run it

```bash
cp .env.example .env    # fill in AION_CLIENT_ID / AION_CLIENT_SECRET
poetry install
poetry run aion serve
```

Talk to it from the terminal chat client:

```bash
npm install -g @terminal-research/aion
aio --url http://localhost:8000 --agent-id showcase
```

Send `help` to get the menu — every demonstration is one keyword away from there.

## What to send, and what you get back

| Send | What happens | Implemented in |
| --- | --- | --- |
| `help` | Menu, as plain text | [src/handlers/menu.py](src/handlers/menu.py) |
| `stream` | One reply arrives a few words at a time, paced, then once as durable history | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `typing` | Two typing indicators that are delivered but never persisted | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `card` | A card composed from typed components, and one referenced by URL | [src/handlers/cards.py](src/handlers/cards.py) |
| `file` | Two file artifacts: inline bytes, and a remote URL | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `data` | A structured data artifact instead of prose | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `composite` | The same artifact saved twice, so the store keeps two versions | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `ask` | The agent asks for input and picks it up on your next turn | [src/handlers/hitl.py](src/handlers/hitl.py) |
| `react` | A reaction is added to your message, then removed | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `metadata` | Custom metadata attached to a message and to an artifact | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `progress` | Progress reported while work is still running | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `task` | An explicit A2A Task, built by the agent, placed in the outbox | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `message` | An explicit A2A Message placed in the outbox | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `fail` | The task ends in the failed state, on purpose | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `context` | What the agent knows about this conversation and its caller | [src/handlers/context.py](src/handlers/context.py) |
| `config` | Configuration values the control plane passed to this deployment | [src/handlers/config.py](src/handlers/config.py) |
| `http` | The custom HTTP routes this agent serves next to A2A | [src/api.py](src/api.py) |

Keywords are case-insensitive and tolerate a leading verb, so `card`, `Show me the card`
and `/card` all select the same demonstration. Anything unrecognized returns the menu.
The card sent by `card` carries a button whose action id is a keyword, so pressing it
is handled by the same handler as typing that keyword.

## How it is put together

```
src/
  commands.py     registry — every demonstration is one entry here
  agent.py        BaseAgent subclass: keyword (or card button) -> handler
  replies.py      shared reply helper that appends the source footer
  streaming.py    chunked streaming without a model, pacing opt-in
  api.py          custom HTTP routes
  handlers/       the demonstrations, grouped by kind
```

`src/commands.py` is the single source of truth: the handler table, the menu, the
response footers, the `/showcase/commands` endpoint and the `skills.examples` list in
`aion.yaml` all come from it. To add a demonstration, add one registry entry and one
handler.

A handler that only talks through `Thread` is a plain coroutine. A handler that must
change session state or place something in the A2A outbox is an async generator that
yields ADK events — `src/agent.py` accepts either.

## Notes on the platform

- **A turn that asks a question ends there.** An ADK agent answers and returns; it does
  not park mid-run. Session state written through `EventActions(state_delta=...)` carries
  an open question into the next turn — but the server only uses
  `DatabaseSessionService` when a database is configured, otherwise it falls back to an
  in-memory service and the question is lost when the process restarts.
- **Artifacts are stored before they are emitted.** The artifact service owns storage, so
  saving the same name again stores a new version rather than extending the previous one,
  and without a configured artifact service the emission is skipped with a warning.
- **Reactions need a provider message.** They target a message in a channel, so they only
  do something when the turn arrived through a distribution.
- **Secret configuration arrives in plaintext.** `config` echoes the values it receives
  because this sample declares none that are secret. Do not echo real ones.
- **Metadata keys under `aion:` are reserved.** Anything else you attach travels untouched.

## Tests

```bash
poetry run pytest
```

`tests/test_commands.py` covers parsing and the registry with no SDK needed;
`tests/test_agent.py` asserts every command has a handler and that dispatch resolves.
