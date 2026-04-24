---
hide:
  - navigation
---

# A Python parser for BlackLab Corpus Query Language

A full-coverage parser for the **[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) Corpus
Query Language (BCQL)** that converts query strings into a
[Pydantic v2](https://docs.pydantic.dev/) AST (Abstract Syntax Tree) with lossless round-trip
reconstruction and structured error reporting.

## Features

- **Complete BCQL coverage**: token queries, sequences, repetitions, spans, lookarounds, captures,
  global constraints, relations, alignments, and built-in functions.
- **Immutable Pydantic v2 AST**: every node is a frozen `BaseModel` subclass with a `node_type`
  discriminator, making inspection and pattern matching straightforward.
- **Lossless BCQL round-trip**: [`to_bcql()`][bcql_py.models.base.BCQLNode.to_bcql] reproduces the
  original query (preserving shorthand forms, quote characters, sensitivity flags, etc.).
- **Position-aware syntax errors**: [`BCQLSyntaxError`][bcql_py.BCQLSyntaxError] carries the original
  query, the 0-based offset, and a caret-annotated message: ready to forward to a user or LLM.
- **Zero runtime dependencies** beyond Pydantic.

## Installation

```bash
pip install bcql_py
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add bcql_py
```

## Quick start

### Parse and reconstruct

```python
from bcql_py import parse

ast = parse('[word="man"]')
ast.to_bcql()  # '[word="man"]'

# Sequences, repetitions, captures, etc. are all supported:
ast = parse('"the" [pos="ADJ"]+ "man"')
ast.to_bcql()  # '"the" [pos="ADJ"]+ "man"'
```

### Handle syntax errors

```python
from bcql_py import parse, BCQLSyntaxError

try:
    parse('[word="man"')        # missing closing bracket
except BCQLSyntaxError as err:
    print(err)
    # Expected RBRACKET at end of token query, got EOF ('')
    #   [word="man"
    #              ^
```

The error carries [`err.query`][bcql_py.BCQLSyntaxError] and
[`err.position`][bcql_py.BCQLSyntaxError] so callers can produce custom diagnostics or feed the
string representation back into an LLM for self-correction: see the
[LLM workflows guide](guides/llm-workflows.md).

### Inspect the AST

```python
from bcql_py import parse
from bcql_py.models import TokenQuery, AnnotationConstraint

ast = parse('[word="man"]')
assert isinstance(ast, TokenQuery)
assert isinstance(ast.constraint, AnnotationConstraint)
ast.constraint.annotation  # 'word'
ast.constraint.value.value  # 'man'
```

Every node is an immutable `pydantic.BaseModel` subclass, so standard Pydantic methods
(`model_dump`, `model_copy`, `model_fields`, etc.) are available.

## Supported BCQL constructs

| Category | Examples |
|---|---|
| Token queries | `[word="man"]`, `"man"`, `[]`, `[pos != "noun"]` |
| Regex & literal strings | `"(wo)?man"`, `l"e.g."`, `"(?-i)Panama"` |
| Boolean constraints | `[lemma="search" & pos="noun"]`, `[a="x" \| b="y"]` |
| Sequences | `"the" "tall" "man"` |
| Repetitions | `[pos="ADJ"]+`, `[]{2,5}`, `"word"?` |
| Spans | `<s/>`, `<s>`, `</s>`, `<ne type="PERS"/>` |
| Position filters | `"baker" within <person/>`, `<s/> containing "dog"` |
| Captures | `A:[pos="ADJ"]`, `A:[] "by" B:[] :: A.word = B.word` |
| Relations | `_ -obj-> _`, `_ -subj-> _ ; -obj-> _`, `^--> "have"` |
| Alignments | `"cat" ==>nl _`, `"cat" ==>nl? _` |
| Lookaround | `(?= "next")`, `(?<= "prev")`, `(?! "not")` |
| Functions | `meet(...)`, `rspan(...)`, `rfield(...)` |

See the [cheatsheet](guides/cheatsheet.md) for a quick-reference table of every operator.

## Development

```bash
git clone https://github.com/BramVanroy/bcql_py.git
cd bcql_py
uv sync

# Run tests and doctests
uv run pytest

# Lint and format
make quality   # check only
make style     # auto-fix
```
