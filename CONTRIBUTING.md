# Contributing

## Adding a sample

A sample lives in `python/agents/<framework>_<name>/` and must be self-contained: someone
should be able to copy that one directory out of the repository and run it.

Every sample has:

- `README.md` — what it demonstrates, how to run it, and a table of what to send and what
  you will see back.
- `aion.yaml` — a filled-in agent definition: `name`, `description`, `version`,
  `input_modes`/`output_modes`, and at least one skill whose `examples` list the inputs the
  sample accepts. UIs surface those examples as suggestions.
- `pyproject.toml`, `poetry.toml`, `.env.example`.
- `src/`, `tests/`.

## Rules

- **No secrets.** `.env` is git-ignored; only `.env.example` is committed, and it carries
  placeholder values.
- **No environment leftovers.** Never commit `.venv/`, `.idea/`, `.ruff_cache/`,
  `__pycache__/`, or `poetry.lock`.
- **Only Aion credentials.** A sample that needs a third-party API key belongs in an
  internal repository, not here. If a sample must call an external service, use one that
  works without a key.
- **Working links.** Any URL a sample emits (an artifact URL, a card URL) must actually
  resolve. Placeholder hosts such as `example.test` make a working feature look broken.
- **Internal extensions stay internal.** Do not enable the daemon or behaviour-evolution
  extensions in a public sample.

## Keeping a sample honest

Where a feature has no equivalent in a given framework, keep the command and have it say
so explicitly. A visible "not available here, and here is why" is more useful to a reader
than a silently missing feature.
