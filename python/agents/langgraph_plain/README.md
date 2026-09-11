# Plain LangGraph Agent

A LangGraph graph with nothing Aion-specific in it, served as an Aion agent as is.

`src/graph.py` imports only `langchain_core` and `langgraph`. It is the graph you would
write without the platform: `MessagesState`, one node that reads the latest
`HumanMessage` and returns an `AIMessage`. Everything the platform adds happens outside
the graph — the SDK turns the inbound A2A message into state, keeps that state per
conversation, and turns the returned message into the reply.

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

The message number grows because the server keeps the graph's state per conversation:
every turn that shares a context id runs with the `messages` accumulated so far, and
the graph never had to store anything itself.

## How it is put together

```
aion.yaml       the agent definition: where the graph is, what it is called
src/graph.py    the graph — no Aion imports
tests/          the graph invoked directly, no server needed
```

## What the SDK did for you

- **Input.** The A2A message became a `HumanMessage` in `state["messages"]`, with its
  content as content blocks — the graph reads them the same way it would read a string.
- **Memory.** The conversation's context id is the graph's thread id, so `messages`
  accumulates across turns without a checkpointer in the code.
- **Output.** The `AIMessage` the node returned became the reply; had the node called a
  model with `astream()`, the tokens would have streamed to the client as they arrived.
- **Everything else.** Cards, artifacts, typing indicators, human-in-the-loop, reactions,
  configuration and custom HTTP routes are one import away — the
  [LangGraph showcase](../langgraph_showcase/README.md) demonstrates each of them.

## Tests

```bash
poetry run pytest
```
