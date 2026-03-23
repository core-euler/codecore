# CodeCore

CodeCore is a provider-agnostic terminal operating system for software development agents.

Current repository state:

- product and architecture are defined;
- runtime package scaffold is in place;
- core contracts exist for providers, policies, telemetry, context, memory, tools, and artifacts;
- runnable MVP behavior is intentionally minimal while the kernel is being built.

## Run

```bash
. .venv/bin/activate
python -m codecore
```

## Test

```bash
. .venv/bin/activate
python -m unittest discover -s tests -v
```
