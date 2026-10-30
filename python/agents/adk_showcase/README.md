# ADK Showcase

A guided tour of what an agent can do on the Aion platform, built with Google ADK.

Send it a keyword and it performs one demonstration, then tells you which SDK call
produced what you just saw and which file it lives in. That call is written in the file
the footer names — no reply helper stands between the two, so every demonstration reads
as the SDK code you would write yourself.

Every answer is text the agent already knows, so what you are looking at is platform
behaviour rather than model output. What a command produces is the task's result, and a
result is an artifact: files, data, a hand-built artifact, or — when the answer is text —
`thread.reply(text_artifact(text))`. The task holds it among its artifacts, and the
server copies no `aion:assistant-answer` from a message for it. Text that is not the
result is a message: the explanation beside a result, a turn that does nothing but say
why (`config` without an environment, `react` without a distribution, `llm` without a
prompt or a model), the question `ask` leaves open, the message `metadata` decorates and
the explanation `fail` sends: a failed task has no result. Two commands stream: `stream`,
which paces its own chunks because that is what it demonstrates, and `llm`, where a
model from the platform's catalog answers and its tokens are the chunks; both answers
are the task's `aion:stream-delta` artifact. `card` is the one command that sends rich
cards; a card is a message, so its explanation goes first and the cards close the turn.
The explicit A2A Message of `message` is that task's answer, and its explanation a
message.

## Run it

```bash
poetry install
poetry run aion serve
```

No credentials are needed for that: every command except `llm` works over a direct
local call. `llm` calls the platform's model service, which needs three things —
`AION_CLIENT_ID` / `AION_CLIENT_SECRET` in `.env` (copy `.env.example`), a turn the
platform delivered, because the model service runs work for the environment's identity
and a direct local call carries none, and a model chosen in the `model` field of the
environment's configuration. Without a model, `llm` says how to choose one, in a
message; without credentials or a platform-delivered turn the SDK refuses the call, and
the task fails with that refusal as its reason.

Talk to it from the terminal chat client:

```bash
npm install -g @terminal-research/aion
aio --url http://localhost:8000 --agent-id showcase
```

Send `help` to get the menu — every demonstration is one keyword away from there.

## What to send, and what you get back

| Send | What happens | Implemented in |
| --- | --- | --- |
| `help` | Menu, as a text artifact | [src/handlers/menu.py](src/handlers/menu.py) |
| `stream` | The answer arrives a few words at a time, paced, as the task's `aion:stream-delta` artifact | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `llm {prompt}` | An `LlmAgent` on the platform's model answers the prompt; its events stream the tokens, no `Thread` involved | [src/handlers/llm.py](src/handlers/llm.py) |
| `thinking` | Two thoughts, kept in the task's `aion:thinking-delta` artifact rather than the history | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `card` | A card composed from typed components, and one referenced by URL | [src/handlers/cards.py](src/handlers/cards.py) |
| `artifact` | An artifact built by hand — its own id, a name, one text part and custom metadata | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `file` | Two file artifacts: inline bytes, and a remote URL | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `data` | A structured data artifact instead of prose | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `composite` | The same artifact saved twice, so the store keeps two versions | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `ask` | The agent asks for input in a message and picks it up on your next turn | [src/handlers/hitl.py](src/handlers/hitl.py) |
| `react` | A reaction is added to your message, then removed | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `metadata` | Custom metadata attached to a message and to an artifact | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `progress` | Progress reported while work is still running | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `task` | An explicit A2A Task, built by the agent, placed in the outbox | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `message` | An explicit A2A Message placed in the outbox | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `fail` | The task ends in the failed state, on purpose, with its reason in a message | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `context` | What the agent knows about this conversation and its caller | [src/handlers/context.py](src/handlers/context.py) |
| `config` | Configuration values the control plane passed to this deployment | [src/handlers/config.py](src/handlers/config.py) |
| `http` | The custom HTTP routes this agent serves next to A2A | [src/api.py](src/api.py) |

Every command except `stream` names the SDK call it demonstrates and the file it lives
in, in a footer at the end of its text answer or of its explanation; `stream` streams
that footer with the rest of its answer.

Keywords are case-insensitive and tolerate a leading verb, so `card`, `Show me the card`
and `/card` all select the same demonstration. Anything unrecognized returns the menu.
The card sent by `card` carries a button whose action id is a keyword, so pressing it
is handled by the same handler as typing that keyword.

## How it is put together

```
src/
  commands.py   registry — every demonstration is one entry here
  agent.py      BaseAgent subclass: keyword (or card button) -> handler
  replies.py    with_footer(): builds the answer text, sends nothing
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

- **A result is an artifact; text around it is a message.** A client reads what a task
  produced from its artifacts, so every result here is one: `text_artifact(text)` builds
  an artifact with one text part, a fresh id and the name `text`, and `artifact` shows
  the same thing built by hand. A task that has an artifact of its own gets no
  `aion:assistant-answer`; one that only sent messages would get its last message copied
  into one. Saving the name `text` again in the same conversation stores the next
  version, so each answer's `metadata.version` counts up from 0.
- **A failed call fails the task.** When the model call of `llm` is refused or fails,
  the handler raises `TaskFailedError`; its explanation becomes the message of the
  FAILED status.
- **An artifact's metadata comes with `thread.reply()`.** The ADK artifact service
  stores the part alone; the artifact's id and name travel with the event that announces
  it, and its custom metadata is the `metadata` passed to `thread.reply()`.
- **A turn that asks a question ends there.** An ADK agent answers and returns; it does
  not park mid-run, so the task of `ask` completes rather than waiting in
  `INPUT_REQUIRED`: the question and its explanation are one message in its history,
  and the answer arrives as a new task in the same conversation. Session state
  written through `EventActions(state_delta=...)` carries the open question into that
  turn — but the server only uses `DatabaseSessionService` when a database is
  configured, otherwise it falls back to an in-memory service and the question is lost
  when the process restarts.
- **Artifacts are stored before they are emitted.** The artifact service owns storage, so
  saving the same name again stores a new version rather than extending the previous one,
  and without a configured artifact service the emission is skipped with a warning.
- **Reactions need a provider message.** They target a message in a channel, so they only
  do something when the turn arrived through a distribution.
- **The model is configuration, not code.** `aion.yaml` declares a `model` field of type
  `llm`; the control plane offers its model catalog for it, and `llm` reads the value
  from the environment on every turn. There is no default, in `aion.yaml` or in the
  code: whoever deploys the agent picks a model, and until the field is set `llm`
  makes no call and says how to set it.
- **A model call needs a principal.** The model service runs work for the environment's
  Daemon Identity, which arrives with a platform-delivered invocation. A direct local
  call has none, so the SDK refuses the call before sending it; `llm` fails the task
  with that refusal as its reason.
- **The Daemon Identity needs `model.execute`.** Its role must allow running models in
  the organization (of the agent roles, Organization Agent does). When the model service
  refuses a call, the reason `llm` fails the task with quotes the service and, by its
  error code, says what to change; the codes are listed under Troubleshoot a request in
  the model service docs.
- **An `LlmAgent` sees the session.** `llm` runs a child `LlmAgent` on the current
  invocation context, so the model's conversation history is the ADK session — every
  earlier user turn in this conversation and every message or streamed answer the agent
  sent, but not its text artifacts: the session records an artifact's version, and its
  text stays in the artifact service.
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
signature, that dispatch resolves, and runs every handler to check what it sends, in
order: a text artifact when the answer is text, the result and a message explaining it
otherwise, a message for a turn that does nothing, and no text event beside them;
`tests/test_llm.py` runs the `llm` handler against a faked agent and checks where the
model id comes from, that a missing prompt or model gets a message, and that a failed
call fails the task with its explanation as the reason.
