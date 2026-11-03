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
prompt or a model, `attachment` without a file), what `ask` says before the task waits —
the question itself is the message of the input-required status — the messages
`metadata` and `post` demonstrate, and the explanation `fail` sends before the task
fails: a failed task has no result, and its reason is the message of the FAILED status.
Three commands stream: `stream` and `sections`, which pace their own chunks because that
is what they demonstrate, and `llm`, where a model from the platform's catalog answers
and its tokens are the chunks; all three answer in the task's `aion:stream-delta`
artifact. `card` is the one command that sends rich cards; a card is a message, so its
explanation goes first and the cards close the turn. The explicit A2A Message of
`message` is that task's answer, and its explanation a message.

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

The SDK the sample installs ships the same client, so from the sample's directory
`poetry run aion chat --url http://localhost:8000 --agent-id showcase` works too. On
macOS it runs a binary bundled with the SDK; elsewhere it needs Node.js.

Send `help` to get the menu — every demonstration is one keyword away from there.

## What to send, and what you get back

| Send | What happens | Implemented in |
| --- | --- | --- |
| `help` | Menu, as a text artifact | [src/handlers/menu.py](src/handlers/menu.py) |
| `stream` | The answer arrives a few words at a time, paced, as the task's `aion:stream-delta` artifact | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `sections` | Two streamed sections with a thought between them; the stream shows both, the task keeps the second | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `llm {prompt}` | An `LlmAgent` on the platform's model answers the prompt; its events stream the tokens, no `Thread` involved | [src/handlers/llm.py](src/handlers/llm.py) |
| `thinking` | Two thoughts, kept in the task's `aion:thinking-delta` artifact rather than the history | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `card` | A card composed from typed components, and one referenced by URL | [src/handlers/cards.py](src/handlers/cards.py) |
| `artifact` | An artifact built by hand — its own id, a name, one text part and custom metadata | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `file` | Two file artifacts: inline bytes, and a remote URL | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `data` | A structured data artifact instead of prose | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `composite` | One artifact delivered as three appended chunks | [src/handlers/artifacts.py](src/handlers/artifacts.py) |
| `ask` | The agent says it needs input, waits in the input-required state with the question as its status message, and answers where it stopped | [src/handlers/hitl.py](src/handlers/hitl.py) |
| `react` | A reaction is added to your message, then removed | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `post` | A message posted without a route, then a reply that carries the route of your message | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `metadata` | Custom metadata attached to a message and to an artifact | [src/handlers/messaging.py](src/handlers/messaging.py) |
| `progress` | Progress reported while work is still running | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `task` | An explicit A2A Task, built by the agent, placed in the outbox | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `message` | An explicit A2A Message placed in the outbox | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `fail` | The task fails on purpose: an explanation in a message, the reason in the message of the FAILED status | [src/handlers/tasks.py](src/handlers/tasks.py) |
| `context` | What the agent knows about this conversation and its caller | [src/handlers/context.py](src/handlers/context.py) |
| `attachment` | The files attached to your message — name, type, size or link | [src/handlers/context.py](src/handlers/context.py) |
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
  streaming.py  the chunked iterator `stream` and `sections` hand to reply()
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
a coroutine, while one that yields an ADK event of its own — the long-running call
`ask` pauses on, or the A2A outbox of `task` and `message` — is an async generator of
ADK events. A turn that resumes `ask` goes to the handler that answers it, whatever its
text says.

## Notes on the platform

- **A result is an artifact; text around it is a message.** A client reads what a task
  produced from its artifacts, so every result here is one: `text_artifact(text)` builds
  an artifact with one text part, a fresh id and the name `text`, and `artifact` shows
  the same thing built by hand. A task that has an artifact of its own gets no
  `aion:assistant-answer`; one that only sent messages gets its last message copied
  into one.
- **A failed task says why.** `fail` on purpose, and `llm` when its model call is
  refused or fails, raise `TaskFailedError`; its reason becomes the message of the
  FAILED status.
- **An artifact goes out as it is.** `thread.reply(artifact)` publishes the A2A
  artifact as it was built — every part, its id, name and own metadata — the way
  `emit_artifact` does, and `emit_artifact` with `append` and `is_last_chunk` builds one
  artifact in chunks, as `composite` shows. The `metadata` argument of `thread.reply()`
  goes on the update event beside the artifact, which is what `metadata` shows. ADK's
  own way, `tool_context.save_artifact`, keeps working beside it — the ADK plain sample
  answers with it — and ADK's `load_artifacts` finds published artifacts too.
- **A question pauses the run.** `ask` makes the long-running `adk_request_input` call
  that ADK's own `request_input` tool makes, and returns. The task waits in
  `INPUT_REQUIRED` with the question as its status message, as it does after a LangGraph
  `interrupt()`, and your reply resumes the same invocation as that call's function
  response. The waiting call lives in the ADK session: the server uses
  `DatabaseSessionService` only when a database is configured, otherwise an in-memory
  service, and a pending question is lost when the process restarts.
- **`reply` routes, `post` does not.** `thread.reply()` adds the route of the inbound
  event to everything it sends, and the control plane delivers it back to where the
  question came from. `thread.post()` adds none of its own: without a `target` the
  control plane delivers its message by the distribution's Reply Mode, and
  `target=MessageActionPayload(...)` sends it somewhere specific. A direct A2A call has
  no channel, so there nothing carries a route.
- **A new stream section replaces the last.** Each `thread.reply()` with an async
  iterator is one section of the `aion:stream-delta` artifact and starts it over. The
  client sees every section on the stream; the task keeps the last. Text that has to
  outlive the next section goes out as a message or an artifact of its own.
- **Files arrive as parts of the message.** `aion_runtime_context.inbox.message` holds
  every part as the server received it, and the invocation's `user_content` holds the
  files as `inline_data` and `file_data` parts for a model. With a file storage backend
  configured, the server stores inline bytes before the agent runs and the agent sees a
  link; without one the bytes arrive as they were sent. The terminal chat client sends
  text, so to try `attachment`, send a message with a file part from an A2A client —
  parts such as
  `[{"text": "attachment"}, {"raw": "<base64>", "filename": "units.csv", "mediaType": "text/csv"}]`.
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
- **An `LlmAgent` sees the session.** `llm` runs a child `LlmAgent` named `llm` on the
  current invocation context, so the model's conversation history is the ADK session:
  every earlier user turn in this conversation, its own earlier answers as its own, and
  what the showcase sent through `Thread` as another agent's words — those events keep
  the root agent as their author, and ADK shows a model another author's words as
  quoted context. Artifacts and thoughts are not in the session, so the model does not
  see them.
- **Secret configuration arrives in plaintext.** `config` echoes the values it receives
  because this sample declares none that are secret. Do not echo real ones.
- **Metadata keys under `aion:` are reserved.** Anything else you attach travels untouched.

## Tests

```bash
poetry run pytest
```

`tests/test_commands.py` covers parsing and the registry with no SDK needed, checks
that the call named in each footer really is written in the file the footer points at,
and that the examples in `aion.yaml` are the registry's;
`tests/test_agent.py` asserts every command has a handler with the one dispatch
signature, that dispatch resolves, and runs every handler to check what it sends, in
order: a text artifact when the answer is text, the result and a message explaining it
otherwise, a message for a turn that does nothing, and no text event beside them. It
also checks the call `ask` pauses on and the turn that resumes it, the reason `fail`
raises, the thoughts of `thinking` and `sections`, the chunks of `composite`, the
missing route of `post`, the files `attachment` describes, and that a card button lands
on the command it names;
`tests/test_llm.py` runs the `llm` handler against a faked agent and checks where the
model id comes from, that a missing prompt or model gets a message, and that a failed
call fails the task with its explanation as the reason.
