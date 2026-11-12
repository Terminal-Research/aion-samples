# ADK Showcase

A guided tour of what an agent can do on the Aion platform, built with Google ADK.

Send it a keyword and it performs one demonstration, then tells you which SDK call
produced what you just saw and which file it lives in. That call is written in the file
the footer names — no reply helper stands between the two, so every demonstration reads
as the SDK code you would write yourself.

Add `native` after a keyword — `stream native`, `artifact native` — and the same
demonstration runs with ADK alone: no `Thread`, no SDK helper, only the ADK events and
services the framework offers once the Aion server runs it. Where ADK has no way of its
own, `… native` says so and names the SDK call to use. The menu marks every command
`native ✓` or `native —`, and the table below says how.

Every answer is text the agent already knows, so what you are looking at is platform
behaviour rather than model output. What a command produces is the task's result, and a
result is an artifact: files, data, a hand-built artifact, or — when the answer is text —
`thread.reply(text_artifact(text))`. The task holds it among its artifacts, and the
server copies no `aion:assistant-answer` from a message for it. Text that is not the
result is a message: the explanation beside a result, what `ask` says before the task waits —
the question itself is the message of the input-required status — the messages
`metadata` and `post` demonstrate, and the explanation `fail` sends before the task
fails: a failed task has no result, and its reason is the message of the FAILED status.
A turn with nothing to do answers with a text artifact that says why: `config` without an
environment, `react` without a distribution, `llm` without a prompt or a model,
`attachment` without a file, and `… native` for what ADK cannot do alone; the server
builds no `aion:assistant-answer` for it. A `native` version that answers with a text
event gets that message copied into `aion:assistant-answer`, as any ADK agent does.
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

| Send | What happens | With ADK alone (`… native`) | Implemented in |
| --- | --- | --- | --- |
| `help` | Menu, as a text artifact |  | [src/commands/help.py](src/commands/help.py) |
| `stream` | The answer arrives a few words at a time, paced, as the task's `aion:stream-delta` artifact | ✓ Event(partial=True) for every chunk, then one event with the whole text | [src/commands/stream.py](src/commands/stream.py) |
| `sections` | Two streamed sections with a thought between them; the stream shows both, the task keeps the second | ✓ every run of partial events in a turn streams a section of its own | [src/commands/sections.py](src/commands/sections.py) |
| `llm {prompt}` | An `LlmAgent` on the platform's model answers the prompt, and reads a file attached to it: the agent reads the user's message as it arrived. Its events stream the tokens, no `Thread` involved | ✓ the events of an LlmAgent, which `llm` already yields; the SDK supplies only the model | [src/commands/llm.py](src/commands/llm.py) |
| `thinking` | Two thoughts, kept in the task's `aion:thinking-delta` artifact rather than the history | — a model's thought parts do not reach the client | [src/commands/thinking.py](src/commands/thinking.py) |
| `card` | A card composed from typed components, and one referenced by URL | — cards belong to the platform | [src/commands/card.py](src/commands/card.py) |
| `artifact` | An artifact built by hand — its own id, a name, one text part and custom metadata | ✓ save_artifact(), which keeps a version of the artifact per save | [src/commands/artifact.py](src/commands/artifact.py) |
| `file` | Two file artifacts: inline bytes, and a remote URL | ✓ save_artifact() with an inline_data part | [src/commands/file.py](src/commands/file.py) |
| `data` | A structured data artifact instead of prose | — an ADK part carries no structured data | [src/commands/data.py](src/commands/data.py) |
| `composite` | One artifact delivered as three appended chunks | — save_artifact() replaces an artifact whole, it has no chunks | [src/commands/composite.py](src/commands/composite.py) |
| `ask` | The agent says it needs input, waits in the input-required state with the question as its status message, and answers where it stopped | ✓ a long-running function call, which `ask` already makes | [src/commands/ask.py](src/commands/ask.py) |
| `react` | A reaction is added to your message, then removed | — reactions belong to the platform | [src/commands/react.py](src/commands/react.py) |
| `post` | A message posted without a route, then a reply that carries the route of your message | — routes belong to the platform | [src/commands/post.py](src/commands/post.py) |
| `metadata` | Custom metadata attached to a message and to an artifact | ✓ Event(custom_metadata=...), which lands in the message's metadata | [src/commands/metadata.py](src/commands/metadata.py) |
| `progress` | Progress reported while work is still running | — ADK has no progress of its own that reaches the client | [src/commands/progress.py](src/commands/progress.py) |
| `task` | An explicit A2A Task, built by the agent, placed in the outbox | — an A2A Task belongs to the platform | [src/commands/task.py](src/commands/task.py) |
| `message` | An explicit A2A Message placed in the outbox | ✓ a text event of the agent | [src/commands/message.py](src/commands/message.py) |
| `fail` | The task fails on purpose: an explanation in a message, the reason in the message of the FAILED status | ✓ any exception raised in the agent, which the caller sees only as an unexpected error | [src/commands/fail.py](src/commands/fail.py) |
| `context` | What the agent knows about this conversation and its caller | ✓ ctx.session.id and ctx.user_id | [src/commands/context.py](src/commands/context.py) |
| `attachment` | The files attached to your message — name, type, size or link | ✓ the inline_data and file_data parts of ctx.user_content | [src/commands/attachment.py](src/commands/attachment.py) |
| `config` | Configuration values the control plane passed to this deployment | — deployment configuration comes from the platform | [src/commands/config.py](src/commands/config.py) |
| `http` | The custom HTTP routes this agent serves next to A2A | — the platform's server mounts the agent's HTTP routes | [src/commands/http.py](src/commands/http.py) |

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
  agent.py      the agent: it reads the turn's keyword and runs that command
  commands/     one file per command; this is what to read
    stream.py   COMMAND, then with_sdk(), then with_adk() when ADK can do it alone
    …
  tour/         the tour's own plumbing; an agent of your own needs none of it
    command.py  Command: the key, a summary, the SDK call, and the native way or why there is none
    routing.py  the keyword (or card button) and `native` of a turn, and the `not_native` answer
    menu.py     the menu and the examples aion.yaml lists
    standins.py a text stream that needs no real model
```

Every command is one file in `src/commands/`, named after its keyword. It starts with
`COMMAND`, which says what the command is, which SDK call it shows, and how ADK does the
same alone or why it cannot. Below it is `with_sdk`, the command done with the SDK, and
`with_adk` when ADK can do it alone. `src/commands/__init__.py` lists the files in menu
order, and the menu, the footers, the `/showcase/commands` endpoint and the
`skills.examples` list in `aion.yaml` all come from that list. To add a demonstration,
add one file and its name there.

Both take `(ctx, argument)`, where `argument` is whatever was typed after the keyword.
One that only talks through `Thread` is a coroutine; one that yields ADK events of its
own — the long-running call `ask` pauses on, the A2A outbox of `task` and `message`,
every `with_adk` — is an async generator. A turn that resumes `ask` goes to
`ask.answer`, whatever its text says.

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
- **`llm` is an ordinary ADK sub-agent.** `create_agent()` declares an `LlmAgent` named
  `llm` in the showcase's `sub_agents`, and the `llm` command runs it the way an ADK agent
  runs a sub-agent, `agent.run_async(ctx)`. ADK then knows every agent that answers in the
  conversation, and the next turn comes back to the showcase. The model is the
  environment's, known only once a turn arrives, so it is given to `aion_lite_llm` as a
  function of the turn's runtime context, which the SDK calls before each request.
- **An `LlmAgent` sees the session.** The `llm` sub-agent runs on the showcase's
  invocation context, so the model's conversation history is the ADK session:
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

`tests/test_commands.py` covers the command files, parsing and the menu, checks
that the call named in each footer really is written in the file the footer points at,
and that the examples in `aion.yaml` are the commands';
`tests/test_agent.py` asserts every command has a handler with the one dispatch
signature, that dispatch resolves, and runs every handler to check what it sends, in
order: a text artifact when the answer is text, the result and a message explaining it
otherwise, a text artifact for a turn that does nothing, and no text event beside them. It
also checks the call `ask` pauses on and the turn that resumes it, the reason `fail`
raises, the thoughts of `thinking` and `sections`, the chunks of `composite`, the
missing route of `post`, the files `attachment` describes, and that a card button lands
on the command it names;
`tests/test_native.py` checks that every command says whether ADK can do it alone, that
the native handlers call nothing from the SDK, what each of them yields, and that
`… native` for the rest names the SDK call to use;
`tests/test_llm.py` checks that `llm` is a declared sub-agent, runs the `llm` handler
against a faked sub-agent and checks where the model id comes from, that a missing prompt or model gets a message, and that a failed
call fails the task with its explanation as the reason.
