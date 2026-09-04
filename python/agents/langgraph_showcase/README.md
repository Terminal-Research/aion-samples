# LangGraph Showcase

A guided tour of what an agent can do on the Aion platform, built with LangGraph.

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
| `help` | Menu, as plain text | [src/nodes/menu.py](src/nodes/menu.py) |
| `stream` | One reply arrives a few words at a time, paced, then once as durable history | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `typing` | Two typing indicators that are delivered but never persisted | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `card` | A card composed from typed components, and one referenced by URL | [src/nodes/cards.py](src/nodes/cards.py) |
| `file` | Two file artifacts: inline bytes, and a remote URL | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `data` | A structured data artifact instead of prose | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `composite` | One artifact delivered as three appended chunks | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `ask` | The agent stops, asks for input, and resumes where it stopped | [src/nodes/hitl.py](src/nodes/hitl.py) |
| `react` | A reaction is added to your message, then removed | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `metadata` | Custom metadata attached to a message and to an artifact | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `progress` | Progress reported while work is still running | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `task` | An explicit A2A Task, built by the agent, placed in the outbox | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `message` | An explicit A2A Message placed in the outbox | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `fail` | The task ends in the failed state, on purpose | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `context` | What the agent knows about this conversation and its caller | [src/nodes/context.py](src/nodes/context.py) |
| `config` | Configuration values the control plane passed to this deployment | [src/nodes/config.py](src/nodes/config.py) |
| `http` | The custom HTTP routes this agent serves next to A2A | [src/api.py](src/api.py) |

Keywords are case-insensitive and tolerate a leading verb, so `card`, `Show me the card`
and `/card` all select the same demonstration. Anything unrecognized returns the menu.
The card sent by `card` carries a button whose action id is a keyword, so pressing it
is handled by the same node as typing that keyword.

## How it is put together

```
src/
  commands.py    registry — every demonstration is one entry here
  router.py      free-form text (or a card button) -> command -> node
  graph.py       one node per registry entry, wired to the router
  state.py       conversation state
  streaming.py   chunked streaming without a model, pacing opt-in
  replies.py     shared reply helper that appends the source footer
  api.py         custom HTTP routes
  nodes/         the demonstrations, grouped by kind
```

`src/commands.py` is the single source of truth: the graph nodes, the menu, the response
footers, the `/showcase/commands` endpoint and the `skills.examples` list in `aion.yaml`
all come from it. To add a demonstration, add one registry entry and one node function.

## Notes on the platform

- **Do not emit anything before `interrupt()` in the same node.** LangGraph replays a node
  from its first line when the graph resumes, so a message sent before the interrupt is
  sent twice. `ask` is split across two nodes for exactly this reason.
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
`tests/test_graph.py` asserts the graph exposes a node for every command.
