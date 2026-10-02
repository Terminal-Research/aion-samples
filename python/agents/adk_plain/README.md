# Plain ADK Agent

An ADK agent with nothing Aion-specific in it, served as an Aion agent as is.

`src/agent.py` imports only `google.adk` and `google.genai`. It is the agent you would
write without the platform: a `BaseAgent` whose `_run_async_impl` reads
`ctx.user_content` and yields one `Event`. Everything the platform adds happens outside
the agent — the SDK turns the inbound A2A message into the session's user event, keeps
the session per conversation, and turns the yielded event into the reply.

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

| Send | What happens |
| --- | --- |
| `Hello there` | `You said 2 word(s): "Hello there". That was message 1 in this conversation.` |
| anything else, same conversation | The same summary, with the message number one higher |

The message number grows because the server keeps one ADK session per conversation:
every turn that shares a context id sees the events accumulated so far, and the agent
never had to store anything itself.

## How it is put together

```
aion.yaml       the agent definition: where the agent is, what it is called
src/agent.py    the agent — no Aion imports
tests/          the agent run directly, no server needed
```

## What the SDK did for you

- **Input.** The A2A message became the session's latest user event and the
  invocation's `user_content`, the way ADK's own runner delivers it.
- **Memory.** The conversation's context id keys the session, so earlier events are
  there on every turn. The session lives in memory unless a database is configured, so
  it does not survive a restart.
- **Output.** The non-partial `Event` the agent yielded became the reply; an `LlmAgent`
  yielding partial events would have streamed its tokens to the client as they arrived.
- **Everything else.** Cards, artifacts, typing indicators, multi-turn state, reactions,
  configuration and custom HTTP routes are one import away — the
  [ADK showcase](../adk_showcase/README.md) demonstrates each of them.

## Tests

```bash
poetry run pytest
```
