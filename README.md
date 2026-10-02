# Aion Samples

Runnable sample agents for the [Aion platform](https://docs.aion.to), two per supported
agent framework. Each sample is self-contained: copy its directory, change the code, and
you have your own agent.

## Samples

| Sample | Framework | What it shows | Requirements |
| --- | --- | --- | --- |
| [langgraph_plain](python/agents/langgraph_plain/README.md) | LangGraph | A graph with no Aion imports, served as is: input into state, reply out of it, conversation remembered between turns | None |
| [adk_plain](python/agents/adk_plain/README.md) | Google ADK | The same with a `BaseAgent`: user content in, one event out, session remembered between turns | None |
| [langgraph_showcase](python/agents/langgraph_showcase/README.md) | LangGraph | Guided tour of every platform feature an agent can use: streaming, a model answer, cards, artifacts, human-in-the-loop, reactions, A2A task/message, runtime context, configuration, custom HTTP routes | Aion credentials for `llm` only |
| [adk_showcase](python/agents/adk_showcase/README.md) | Google ADK | The same tour, written with the Google ADK authoring toolkit | Aion credentials for `llm` only |

Start with a plain sample if you already have a graph or an agent: it shows what the
platform does around your code before you use anything of its own. Move to a showcase
to see each platform feature on its own, one keyword per feature.

Both showcase agents expose the same keywords, so you can read whichever framework you
work in and skip the other. Where a framework's own mechanism differs — how a turn waits
for the user, how an artifact grows — each sample explains its own, in its own terms.

The showcase agents write their own replies, so what you see is platform behaviour rather
than model output. The one exception is the `llm` command, where a model from the Aion
control plane catalog answers through the platform's model service — on the same
credentials, with **no model provider key anywhere in the samples**. The model itself is
a configuration field of the deployment, chosen from the catalog per environment.

## Running a sample

```bash
cd python/agents/langgraph_showcase
poetry install
poetry run aion serve
```

Then talk to it from the terminal chat client:

```bash
npm install -g @terminal-research/aion
aio --agent-id showcase --url http://localhost:8000
```

Send `help` to get the list of commands. For a plain sample use `--agent-id plain` and
send anything.

No credentials are needed to run a sample. They come in with the `llm` command of the
showcases, which calls the platform's model service: put `AION_CLIENT_ID` /
`AION_CLIENT_SECRET` in `.env` (copy `.env.example`) — and note that the model service
also needs a turn the platform delivered, so `llm` answers with an explanation, not a
model, over a direct local call.

## Repository layout

```
python/
  agents/
    langgraph_plain/
    adk_plain/
    langgraph_showcase/
    adk_showcase/
```

The `python/` level exists so samples for other languages can be added beside it without
moving anything.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
