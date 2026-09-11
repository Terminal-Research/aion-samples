# LangGraph Showcase

A guided tour of what an agent can do on the Aion platform, built with LangGraph.

Send it a keyword and it performs one demonstration, then tells you which SDK call
produced what you just saw and which file it lives in. That call is written in the file
the footer names — no reply helper stands between the two, so every demonstration reads
as the SDK code you would write yourself.

Every reply is text the agent already knows, sent with `thread.reply(text)`, so what you
are looking at is platform behaviour rather than model output. Two commands stream:
`stream`, which paces its own chunks because that is what it demonstrates, and `llm`,
where a model from the platform's catalog answers and its tokens are the chunks. `card`
is the one command that sends a rich card; everything else is plain text.

## Run it

```bash
poetry install
poetry run aion serve
```

No credentials are needed for that: every command except `llm` works over a direct
local call. `llm` calls the platform's model service, which needs two things —
`AION_CLIENT_ID` / `AION_CLIENT_SECRET` in `.env` (copy `.env.example`) and a turn the
platform delivered, because the model service runs work for the environment's identity
and a direct local call carries none. Until then, `llm` explains that in its reply
instead of failing.

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
| `llm {prompt}` | A model answers the prompt; its tokens stream straight out of the model call, no `Thread` involved | [src/nodes/llm.py](src/nodes/llm.py) |
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
  commands.py   registry — every demonstration is one entry here
  router.py     free-form text (or a card button) -> command key -> node name
  graph.py      every node and edge, spelled out one line at a time
  state.py      conversation state
  streaming.py  the chunked iterator the `stream` command hands to reply()
  replies.py    with_footer(): builds the reply text, sends nothing
  api.py        custom HTTP routes, registered with the server
  nodes/        the demonstrations, grouped by kind
```

`src/commands.py` is the single source of truth for what the agent advertises: the menu,
the response footers, the `/showcase/commands` endpoint and the `skills.examples` list in
`aion.yaml` all come from it. The graph is not generated from it — nodes are named after
command keys and wired by hand, so the wiring is readable as LangGraph rather than as a
loop. To add a demonstration, add one registry entry, one node function, and one
`add_node`/`add_edge` pair in `src/graph.py`.

Each node ends by returning the message it posted in `{"messages": [reply]}`, which is
what accumulates the conversation history the `context` command counts.

## Notes on the platform

- **Do not emit anything before `interrupt()` in the same node.** LangGraph replays a node
  from its first line when the graph resumes, so a message sent before the interrupt is
  sent twice. `ask` is split across two nodes for exactly this reason.
- **Reactions need a provider message.** They target a message in a channel, so they only
  do something when the turn arrived through a distribution.
- **The model is configuration, not code.** `aion.yaml` declares a `model` field of type
  `llm`; the control plane offers its model catalog for it, and `llm` reads the value
  from the environment on every turn. The code keeps the same default for turns that
  carry no environment, because the default in `aion.yaml` is applied by the control
  plane, not by the SDK.
- **A model call needs a principal.** The model service runs work for the environment's
  Daemon Identity, which arrives with a platform-delivered invocation. A direct local
  call has none, so the SDK refuses the call before sending it; `llm` shows that
  refusal in its reply.
- **Secret configuration arrives in plaintext.** `config` echoes the values it receives
  because this sample declares none that are secret. Do not echo real ones.
- **Metadata keys under `aion:` are reserved.** Anything else you attach travels untouched.

## Tests

```bash
poetry run pytest
```

`tests/test_commands.py` covers parsing and the registry with no SDK needed, and checks
that the call named in each footer really is written in the file the footer points at;
`tests/test_graph.py` asserts the graph exposes a node for every command;
`tests/test_llm.py` runs the `llm` node against a faked model and checks where the
model id comes from and how a failed call is reported;
`tests/test_hitl.py` checks that the answer resuming `ask` is read from the content
blocks the server delivers.
