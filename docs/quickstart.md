# Quickstart

## Install

```bash
pip install bcql_py
# or:
uv add bcql_py
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

[`BCQLSyntaxError`][bcql_py.exceptions.BCQLSyntaxError] exposes the original query and the error position so
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

## Validate against a corpus

Pass a [`CorpusSpec`][bcql_py.CorpusSpec] to [`parse()`][bcql_py.parse] to enforce corpus-specific
rules (which annotations exist, which closed-class values are allowed, whether relations or
alignment are supported). See the [tagset validation guide](guides/tagset-validation.md) for
the full picture.

```python
from bcql_py import CorpusSpec, parse

spec = CorpusSpec(
    open_attributes={"word", "lemma"},
    closed_attributes={"pos": {"NOUN", "VERB", "ADJ"}},
    strict_attributes=True,
)
parse('[pos="NOUN"]', spec=spec)   # ok
parse('[pos="NUMBER"]', spec=spec) # raises BCQLValidationError
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

- [Guides](guides/index.md): a number of guides related to this library specifically and BCQL in general.
- [Example scripts](https://github.com/BramVanroy/bcql_py/tree/main/examples).
