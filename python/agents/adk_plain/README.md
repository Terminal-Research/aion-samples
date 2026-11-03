# Plain ADK Agent

An ADK agent with nothing Aion-specific in it, served as an Aion agent as is.

`src/agent.py` imports only `google.adk` and `google.genai`. It is the agent you would
write without the platform: a `BaseAgent` whose `_run_async_impl` reads
`ctx.user_content`, saves its answer as an artifact with ADK's own
`CallbackContext.save_artifact`, and yields one `Event` recording that save. Everything
the platform adds happens outside the agent — the SDK turns the inbound A2A message into
the session's user event, keeps the session per conversation, and sends the saved
artifact to the client as the task's result.

## Run it

```bash
poetry install
poetry run aion serve
```

No credentials are needed. Talk to it from the terminal chat client:

```bash
npm install -g @terminal-research/aion
aio --url http://localhost:8000 --agent-id plain
```

## What to send, and what you get back

| Send | What you get back |
| --- | --- |
| `Hello there` | The artifact `answer`: `You said 2 word(s): "Hello there". That was message 1 in this conversation.` |
| anything else, same conversation | The same summary, with the message number one higher, as the next version of `answer` |

The message number grows because the server keeps one ADK session per conversation:
every turn that shares a context id sees the events accumulated so far, and the agent
never had to store anything itself.

The answer is the task's only artifact and its history holds only your message: the
agent sends no message, so the server copies no `aion:assistant-answer` either.

## How it is put together

```
aion.yaml       the agent definition: where the agent is, what it is called
src/agent.py    the agent — no Aion imports
tests/          the agent run directly on ADK's in-memory services, no server needed
```

## What the SDK did for you

- **Input.** The A2A message became the session's latest user event and the
  invocation's `user_content`, the way ADK's own runner delivers it.
- **Memory.** The conversation's context id keys the session, so earlier events are
  there on every turn. The session lives in memory unless a database is configured, so
  it does not survive a restart. The agent's own events hold no text: the session
  records which version of `answer` each turn saved, and the text stays in the
  artifact service.
- **Output.** The SDK gives the invocation an artifact service, so `save_artifact`
  works as under ADK's own `Runner`. For the event's `artifact_delta` it loads the saved
  version and sends it to the client as an A2A artifact named after the file, `answer`,
  with the version in `metadata.version` — 0 on the first turn of a conversation, one
  higher on each after it. A task with an artifact of its own has its result, so the
  server builds no `aion:assistant-answer`. Had the agent yielded the text as an event's
  content instead, the client would have received it as a message, and the server would
  have copied that message into an `aion:assistant-answer`.
- **Everything else.** Cards, artifacts, thoughts, human-in-the-loop, reactions,
  configuration and custom HTTP routes are one import away — the
  [ADK showcase](../adk_showcase/README.md) demonstrates each of them.

## Tests

```bash
poetry run pytest
```

`tests/test_agent.py` runs the agent on ADK's in-memory session and artifact services and
checks that its one event carries no content and records a saved `answer`, whose text
quotes the message and counts the turns.
