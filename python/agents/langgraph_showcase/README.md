# LangGraph Showcase

A guided tour of what an agent can do on the Aion platform, built with LangGraph.

Send it a keyword and it performs one demonstration, then tells you which SDK call
produced what you just saw and which file it lives in. That call is written in the file
the footer names — no reply helper stands between the two, so every demonstration reads
as the SDK code you would write yourself.

Every answer is text the agent already knows, so what you are looking at is platform
behaviour rather than model output. What a command produces is the task's result, and a
result is an artifact: files, data, a hand-built artifact, or — when the answer is text —
a text artifact sent with `thread.reply(text_artifact(text))`. Three commands stream:
`stream` and `sections`, which pace their own chunks because that is what they
demonstrate, and `llm`, where a model from the platform's catalog answers and its tokens
are the chunks; all three answer in the task's `aion:stream-delta` artifact. `card` is
the one command that sends rich cards, and a card is a message.

Text that is not the result is a message:

- the explanation beside a result — after the artifacts of `artifact`, `file`, `data`,
  `composite` and `metadata`, after the explicit Task of `task`, after the streamed
  answers of `sections` and `llm`, before the explicit Message of `message`, which is
  that task's answer, and before the cards of `card`, which close the turn;
- a turn that does nothing but say why: `config` without an environment, `react`
  without a distribution, `llm` without a prompt or a model, `attachment` without a
  file;
- what `ask` says before the task waits in the input-required state — the question
  itself is the message of that status;
- the explanation `fail` sends before the task fails;
- the messages that are themselves the demonstration — the message `metadata` attaches
  metadata to, the message `post` posts, and the explicit A2A Message and Task that
  `message` and `task` place in the outbox.

A task that fails says why in the message of its FAILED status. `fail` does it on
purpose and a refused or failed model call does it in `llm`: the node raises
`TaskFailedError`, and its reason becomes that message.

Progress (`progress`) and thoughts (`thinking`) go to the task's `aion:thinking-delta`
artifact, which is neither a message nor a result.

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
| `help` | Menu, as a text artifact | [src/nodes/menu.py](src/nodes/menu.py) |
| `stream` | The answer arrives a few words at a time, paced, as the task's `aion:stream-delta` artifact | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `sections` | Two streamed sections with a thought between them; the stream shows both, the task keeps the second | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `llm {prompt}` | A model answers the prompt; its tokens stream straight out of the model call, no `Thread` involved | [src/nodes/llm.py](src/nodes/llm.py) |
| `thinking` | Two thoughts, kept in the task's `aion:thinking-delta` artifact rather than the history | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `card` | A card composed from typed components, and one referenced by URL | [src/nodes/cards.py](src/nodes/cards.py) |
| `artifact` | An artifact built by hand from `a2a.types.Artifact` — its own id, a name, one text part and custom metadata — then a message explaining it | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `file` | Two file artifacts: inline bytes, and a remote URL | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `data` | A structured data artifact instead of prose | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `composite` | One artifact delivered as three appended chunks | [src/nodes/artifacts.py](src/nodes/artifacts.py) |
| `ask` | The agent says it needs input, waits in the input-required state with the question as its status message, and answers where it stopped | [src/nodes/hitl.py](src/nodes/hitl.py) |
| `react` | A reaction is added to your message, then removed | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `post` | A message posted without a route, then a reply that carries the route of your message | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `metadata` | Custom metadata attached to a message and to a data artifact | [src/nodes/messaging.py](src/nodes/messaging.py) |
| `progress` | Progress reported while work is still running | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `task` | An explicit A2A Task, built by the agent, placed in the outbox | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `message` | An explicit A2A Message placed in the outbox | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `fail` | The task fails on purpose: an explanation in a message, the reason in the message of the FAILED status | [src/nodes/tasks.py](src/nodes/tasks.py) |
| `context` | What the agent knows about this conversation and its caller | [src/nodes/context.py](src/nodes/context.py) |
| `attachment` | The files attached to your message — name, type, size or link | [src/nodes/context.py](src/nodes/context.py) |
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
  streaming.py  the chunked iterator `stream` and `sections` hand to reply()
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

A node whose answer is a text artifact returns no message: `{}`, or only the other
state keys it sets. A message returned into `messages` would be sent to the client as a
message beside the artifact. A node that sends a message returns it into `messages`, so
the conversation keeps it; the server recognises it as already sent. The `messages` state
therefore holds the user's messages, the messages the agent sent — explanations, what
`ask` says before it waits, the message `post` posts — and the streamed answers of
`stream`, `sections` and `llm`, and that is what the `context` command counts. An answer
sent as an artifact is not in graph state, so a later model call does not see it. A node
that raises, as `fail` does, returns nothing: its explanation went out, but the state
does not keep it.

`a2a_outbox` is declared with `A2AOutboxField`. The server reads the outbox from the
updates of the run that wrote it, and on that field LangGraph does not checkpoint it:
the next turn does not find the last one's outbox in its state.

## Notes on the platform

- **Do not emit anything before `interrupt()` in the same node.** LangGraph replays a node
  from its first line when the graph resumes, so a message sent before the interrupt is
  sent twice. `ask` is split across two nodes for exactly this reason. The value given to
  `interrupt()` is the question: it becomes the message of the input-required status.
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
- **Files arrive as parts of the message.** `context.inbox.message` holds every part as
  the server received it, and `messages` holds the files as file blocks for a model.
  With a file storage backend configured, the server stores inline bytes before the
  agent runs and the agent sees a link; without one the bytes arrive as they were sent.
  The terminal chat client sends text, so to try `attachment`, send a message with a
  file part from an A2A client — parts such as
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
  refuses a call, `llm` quotes the service's reason and, by its error code, says what to
  change; the codes are listed under Troubleshoot a request in the model service docs.
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
`tests/test_graph.py` asserts the graph exposes a node for every command;
`tests/test_answers.py` runs the nodes with the thread captured and checks what each
command sends: a text artifact when the answer is text, and a message kept in state for
an explanation beside a result, a turn that does nothing and the demonstrated messages;
the thoughts of `thinking` and `sections`, the chunk flags of `composite`, the question
`ask` waits on, the reason `fail` raises, the outbox of `task` and `message`, the
missing route of `post`, the files `attachment` describes, and that a card button lands
on the command it names;
`tests/test_llm.py` runs the `llm` node against a faked model and checks where the
model id comes from, that a missing prompt or model gets a message, and that a failed
call fails the task with its explanation as the reason;
`tests/test_hitl.py` checks that the answer resuming `ask` is read from the content
blocks the server delivers.
