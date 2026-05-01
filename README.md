# A Python parser for BlackLab Corpus Query Language

[![Documentation](https://img.shields.io/badge/documentation-4051b5)](https://bramvanroy.github.io/bcql_py/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bcql_py)
[![codecov](https://codecov.io/gh/BramVanroy/bcql_py/branch/main/graph/badge.svg)](https://codecov.io/gh/BramVanroy/bcql_py)
[![Interrogate coverage](https://raw.githubusercontent.com/BramVanroy/bcql_py/main/.github/interrogate_badge.svg)](https://github.com/BramVanroy/bcql_py/actions/workflows/interrogate-badge.yml)
[![License](https://img.shields.io/github/license/BramVanroy/bcql_py)](LICENSE)

<!-- --8<-- [start:overview] -->

A full-coverage Python parser for the **[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) Corpus
Query Language (BCQL)** that converts query strings into a
[Pydantic v2](https://docs.pydantic.dev/) AST (Abstract Syntax Tree) with lossless round-trip
reconstruction and structured error reporting.

To get started, you can check out:

- [A Quickstart guide](https://bramvanroy.github.io/bcql_py/quickstart/)
- ``bcql_py`` and BCQL general [guides](https://bramvanroy.github.io/bcql_py/guides/)
- The full [API reference](https://bramvanroy.github.io/bcql_py/api/top_level/)
- [Python code examples](https://github.com/BramVanroy/bcql_py/tree/main/examples)
- A [Gradio demo](https://huggingface.co/spaces/BramVanroy/bcql_py_validation)

## Features

- **Complete BCQL coverage**: token queries, sequences, repetitions, spans, lookarounds, captures,
  global constraints, relations, alignments, and built-in functions.
- **Immutable Pydantic v2 AST**: every node is a frozen `BaseModel` subclass with a `node_type`
  discriminator, making inspection and pattern matching straightforward.
- **Lossless BCQL round-trip**: [`to_bcql()`](https://bramvanroy.github.io/bcql_py/api/models/base/#bcql_py.models.base.BCQLNode.to_bcql)
  reproduces the original query (preserving shorthand forms, quote characters, sensitivity flags, etc.).
- **Position-aware syntax errors**: [`BCQLSyntaxError`](https://bramvanroy.github.io/bcql_py/api/exceptions/#bcql_py.BCQLSyntaxError)
  carries the original query, the 0-based offset, and a caret-annotated message: ready to forward to
  a user or LLM.
- **Optional semantic validation**: a [`CorpusSpec`](https://bramvanroy.github.io/bcql_py/api/validation/#bcql_py.validation.spec.CorpusSpec)
  describes which annotations, span tags, alignment fields, and dependency relations your corpus
  supports. Pass it as ``parse(query, spec=spec)`` to catch typos and unsupported features before
  they reach the corpus. See the [tagset validation guide](https://bramvanroy.github.io/bcql_py/guides/tagset-validation/).
- **Zero runtime dependencies** beyond Pydantic.

## Installation

```bash
pip install bcql_py
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add bcql_py
```

## Try the demo

A small Gradio app under [`app/`](https://github.com/BramVanroy/bcql_py/tree/main/app)
lets you paste a BCQL query, pick or build a `CorpusSpec`, and inspect parse +
validation results. The hosted demo runs on Hugging Face Spaces at
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

After installation, hooks run automatically on every `git commit`.
We do style chechking with ruff and type-checking with mypy.
You can also run them manually across the whole repo:

```bash
uv run pre-commit run --all-files
```

To work on documentation locally:

```bash
make docs
```

You can/should run tests before pushing to the remote, although
a Github workflow will run those anyway on push. To run them locally:

```bash
make test
```

<!-- --8<-- [end:overview] -->

## ANTLR to generate the needed tools

BlackLab uses ANTLR to generate the parser/lexer in Java based on a
[g4 file](https://github.com/instituutnederlandsetaal/BlackLab/blob/e248fc2acf2b8cf44deb2564e8b24138b140d4ca/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4#L1-L97).
We could similarly generate Python files. However, after trying it out, I find the files obfuscated
and unclear and I'm not fond of requiring an extra external (Java-based) library. That is not a slight to ANTLR;
I am simply not familiar with the tool: I am sure it is incredibly powerful and useful if you know
how to use it. To keep a clearer view of this library I therefore strive to make a Python-native
implementation that is true to spec. It's also just a fun project that I do not wish to "automate
away" (though I might regret that later). At a later time (TODO) I might implement functionality to
cross-validate our implementation with the generated ANTLR parser and lexer. For now I will be
satisfied with high coverage testing. In case of doubt I have followed the Bcql.g4 file.

If you'd like to try the ANTLR route yourself, you can try it as follows:

1. Install requirements (not included in our pyproject.toml file, you'll need to download these
   yourself!)

   ```sh
   uv pip install requests antlr4-tools antlr4-python3-runtime
   ```

2. Download the BlackLab G4 definition from GitHub. You can optionally specify a `--branch` or
   `--tag`, defaults to `--branch dev`.

   ```sh
   uv run python scripts/get_bcql_g4.py
   # Saved to parser/Bcql.g4
   cd parser/
   ```

3. Run ANTLR (you can update `-v` to [the latest version](https://github.com/antlr/antlr4/releases)
   if needed)

   ```sh
   antlr4 -v 4.13.2 -Dlanguage=Python3 Bcql.g4
   ```

## Acknowledgments

- [BlackLab](https://blacklab.ivdnt.org/)
- Robert Nystrom's guide on ["Crafting Interpreters"](https://craftinginterpreters.com/scanning.html),
  specifically the part on "Scanning". Token types and error handling in `bcql_py` is heavily
  inspired by his work.
- Jamis Buck's [blog post on recursive descent parsers](https://weblog.jamisbuck.org/2015/7/30/writing-a-simple-recursive-descent-parser.html)
- Berkeley [course notes on BNF](https://cs61a.org/study-guide/bnf/)
