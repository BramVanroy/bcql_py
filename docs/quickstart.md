# Quickstart

## Install

```bash
pip install bcql-py
# or:
uv add bcql-py
```

## Parse a query

[`parse()`][bcql_py.parse] runs the lexer and the recursive-descent parser and returns the root
[`BCQLNode`][bcql_py.models.base.BCQLNode]. The returned tree is a frozen Pydantic v2 model:
inspect it, pattern-match on `node_type`, or round-trip it back to BCQL.

```python
from bcql_py import parse

ast = parse('[word="man"]')
ast.node_type       # 'token_query'
ast.to_bcql()       # '[word="man"]'
```

## Reconstruct the query

Every node implements [`to_bcql()`][bcql_py.models.base.BCQLNode.to_bcql]. The output is
guaranteed to re-parse to an AST that is `==` to the original:

```python
from bcql_py import parse

source = '"the" [pos="ADJ"]+ "man"'
ast = parse(source)
assert parse(ast.to_bcql()) == ast
```

See [AST & parser design](guides/ast-design.md) for the full picture of the AST hierarchy.

## Handle errors

[`BCQLSyntaxError`][bcql_py.BCQLSyntaxError] exposes the original query and the error position so
you can render them inline or forward them to another system.

```python
from bcql_py import parse, BCQLSyntaxError

try:
    parse('[word=')
except BCQLSyntaxError as err:
    err.position        # int: 0-based character offset
    err.query           # str: the original query
    str(err)            # Full message with a caret under err.position
```

## Tokenize without parsing

Need just the token stream (e.g. for syntax highlighting)?
Use [`tokenize()`][bcql_py.tokenize]:

```python
from bcql_py import tokenize

tokens = tokenize('"man"')
for tok in tokens:
    print(tok.type.name, tok.value, tok.position)
```

## Next steps

- [Token queries](guides/tokens.md): the core building block.
- [Relations](guides/relations.md): dependency queries and root relations.
- [Parallel corpora](guides/parallel.md): cross-language alignment queries.
- [LLM workflows](guides/llm-workflows.md): agentic retry loops.
- [Example scripts](https://github.com/BramVanroy/bcql-py/tree/main/examples).
