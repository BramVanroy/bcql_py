---
hide:
  - navigation
---

# A Python parser for BlackLab Corpus Query Language

A full-coverage Python parser for the **[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/)
Corpus Query Language (BCQL)** that converts query strings into a
[Pydantic v2](https://docs.pydantic.dev/) AST (Abstract Syntax Tree) with
lossless round-trip reconstruction and structured error reporting.

To get started, you can check out:

- [A Quickstart guide](quickstart.md)
- `bcql_py` and BCQL general [guides](guides/index.md)
- The full [API reference](api/top_level.md)
- [Python code examples](https://github.com/BramVanroy/bcql_py/tree/main/examples)
- A [Gradio demo](https://huggingface.co/spaces/BramVanroy/bcql_py_validation)

## Features

- **Complete BCQL coverage**: token queries, sequences, repetitions, spans,
  lookarounds, captures, global constraints, relations, alignments, and
  built-in functions.
- **Immutable Pydantic v2 AST**: every node is a frozen `BaseModel` subclass
  with a `node_type` discriminator, making inspection and pattern matching
  straightforward.
- **Lossless BCQL round-trip**:
  [`to_bcql()`](api/models/base.md#bcql_py.models.base.BCQLNode.to_bcql)
  reproduces the original query, preserving shorthand forms, quote
  characters, and sensitivity flags.
- **Position-aware syntax errors**:
  [`BCQLSyntaxError`](api/exceptions.md#bcql_py.exceptions.BCQLSyntaxError)
  carries the original query, the 0-based offset, and a caret-annotated
  message ready to forward to a user or LLM.
- **Optional semantic validation**: a
  [`CorpusSpec`](api/validation.md#bcql_py.validation.spec.CorpusSpec)
  describes which annotations, span tags, alignment fields, and dependency
  relations your corpus supports. Pass it as `parse(query, spec=spec)` to
  catch typos and unsupported features before they reach the corpus. See the
  [tagset validation guide](guides/tagset-validation.md).
- **Zero runtime dependencies** beyond Pydantic.

## Installation

```bash
pip install bcql_py
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add bcql_py
```

## Try the Demo

A small Gradio app under
[`app/`](https://github.com/BramVanroy/bcql_py/tree/main/app) lets you paste a
BCQL query, pick or build a `CorpusSpec`, and inspect parse and validation
results. The hosted demo runs on Hugging Face Spaces at
[BramVanroy/bcql_py_validation](https://huggingface.co/spaces/BramVanroy/bcql_py_validation).

To run it locally:

```sh
uv sync --group app
uv run python app/app.py
```

## Development

Clone and set up the project:

```bash
git clone https://github.com/BramVanroy/bcql_py.git
cd bcql_py
uv sync --dev
```

Enable pre-commit hooks:

```bash
uv run pre-commit install
```

After installation, hooks run automatically on every `git commit`. We do style
checking with ruff and type-checking with mypy. You can also run them manually
across the whole repo:

```bash
uv run pre-commit run --all-files
```

To work on documentation locally:

```bash
make serve-docs
```

This rebuilds a fresh local mike preview before serving it, which avoids
re-using stale versioned docs while testing.

You can and should run tests before pushing to the remote, although a GitHub
workflow will run those anyway on push. To run them locally:

```bash
make test
```
