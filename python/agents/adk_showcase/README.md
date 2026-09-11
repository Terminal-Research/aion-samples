# ADK Showcase

A guided tour of what an agent can do on the Aion platform, built with Google ADK.

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
| `help` | Menu, as plain text | [src/handlers/menu.py](src/handlers/menu.py) |
| `stream` | One reply arrives a few words at a time, paced, then once as durable history | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `llm {prompt}` | An `LlmAgent` on the platform's model answers the prompt; its events stream the tokens, no `Thread` involved | [src/handlers/llm.py](src/handlers/llm.py) |
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
  commands.py   registry — every demonstration is one entry here
  agent.py      BaseAgent subclass: keyword (or card button) -> handler
  replies.py    with_footer(): builds the reply text, sends nothing
  streaming.py  the chunked iterator the `stream` command hands to reply()
  api.py        custom HTTP routes, registered with the server
  handlers/     the demonstrations, grouped by kind
```

`src/commands.py` is the single source of truth for what the agent advertises: the menu,
the response footers, the `/showcase/commands` endpoint and the `skills.examples` list in
`aion.yaml` all come from it. Dispatch is not derived from it — `HANDLERS` in
`src/agent.py` maps keys to handlers by hand. To add a demonstration, add one registry
entry, one handler, and one line in that table.

Every handler has the same signature, `(ctx, argument)`, where `argument` is whatever
was typed after the keyword; a handler that accepts none ignores it. The only thing
dispatch tells apart is what a handler returns: one that only talks through `Thread` is
a coroutine, while one that must change session state or place something in the A2A
outbox is an async generator of ADK events.

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
- **The model is configuration, not code.** `aion.yaml` declares a `model` field of type
  `llm`; the control plane offers its model catalog for it, and `llm` reads the value
  from the environment on every turn. The code keeps the same default for turns that
  carry no environment, because the default in `aion.yaml` is applied by the control
  plane, not by the SDK.
- **A model call needs a principal.** The model service runs work for the environment's
  Daemon Identity, which arrives with a platform-delivered invocation. A direct local
  call has none, so the SDK refuses the call before sending it; `llm` shows that
  refusal in its reply.
- **An `LlmAgent` sees the session.** `llm` runs a child `LlmAgent` on the current
  invocation context, so the model's conversation history is the ADK session — every
  earlier turn in this conversation, including the showcase's own replies.
- **Secret configuration arrives in plaintext.** `config` echoes the values it receives
  because this sample declares none that are secret. Do not echo real ones.
- **Metadata keys under `aion:` are reserved.** Anything else you attach travels untouched.

## Tests

```bash
poetry run pytest
```

`tests/test_commands.py` covers parsing and the registry with no SDK needed, and checks
that the call named in each footer really is written in the file the footer points at;
`tests/test_agent.py` asserts every command has a handler with the one dispatch
signature, and that dispatch resolves;
`tests/test_llm.py` runs the `llm` handler against a faked agent and checks where the
model id comes from and how a failed call is reported.
