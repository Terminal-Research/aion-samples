# Aion Samples

Runnable sample agents for the [Aion platform](https://docs.aion.to), one per supported
agent framework. Each sample is self-contained: copy its directory, change the code, and
you have your own agent.

## Samples

| Sample | Framework | What it shows | Requirements |
| --- | --- | --- | --- |
| [langgraph_showcase](python/agents/langgraph_showcase/README.md) | LangGraph | Guided tour of every platform feature an agent can use: streaming, cards, artifacts, human-in-the-loop, reactions, A2A task/message, runtime context, configuration, custom HTTP routes | Aion credentials only |
| [adk_showcase](python/agents/adk_showcase/README.md) | Google ADK | The same tour, written with the Google ADK authoring toolkit | Aion credentials only |

Both showcase agents expose the same keywords, so you can read whichever framework you
work in and skip the other. Where a framework's own mechanism differs — how a turn waits
for the user, how an artifact grows — each sample explains its own, in its own terms.

The showcase agents write their own replies, so what you see is platform behaviour rather
than model output. The one exception is the `llm` command, where a model from the Aion
control plane catalog answers through the platform's model service — on the same
credentials, with **no model provider key anywhere in the samples**.

## Running a sample

```bash
cd python/agents/langgraph_showcase
cp .env.example .env   # fill in AION_CLIENT_ID / AION_CLIENT_SECRET
poetry install
poetry run aion serve
```

Then talk to it from the terminal chat client:

```bash
npm install -g @terminal-research/aion
aio --agent-id showcase --url http://localhost:8000
```

Send `help` to get the list of commands.

## Repository layout

```
python/
  agents/
    langgraph_showcase/
    adk_showcase/
```

The `python/` level exists so samples for other languages can be added beside it without
moving anything.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
