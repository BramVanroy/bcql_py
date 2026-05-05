# AST and parser design

This guide explains how to reason about the internals of `bcql_py` without reading every model
and parser method.

## Design goals

The implementation optimises for three goals:

1. **Full BCQL coverage**: all token queries, sequences, repetitions, spans, lookaround, captures,
   global constraints, relations, and alignments supported by
   [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/).
2. **Functionally lossless round-trip**: `parse(query).to_bcql()` reproduces the original query,
   attempting to maximally retain quote style and shorthand forms.
3. **Position-aware diagnostics**: [`BCQLSyntaxError`][bcql_py.exceptions.BCQLSyntaxError] carries the
   original source and a character offset, so downstream tools (editors, LLMs) can point users
   directly at the problem.

## The pipeline

```
BCQL string  -->  tokenize()  -->  tuple[Token, ...]  -->  BCQLParser  -->  BCQLNode (AST)
                                                                                  |
                                                                       (optional) validate()
                                                                                  |
                                                                         to_bcql() / model_dump()
```

- [`tokenize()`][bcql_py.tokenize] is implemented by [`BCQLLexer`][bcql_py.parser.lexer.BCQLLexer].
- [`parse_from_tokens()`][bcql_py.parse_from_tokens] drives
  [`BCQLParser`][bcql_py.parser.parser.BCQLParser].
- [`parse()`][bcql_py.parse] is the convenience wrapper that combines both. It also accepts a
  ``spec=`` argument that, when provided, runs [`validate()`][bcql_py.validate] against the
  resulting AST before returning it; see the [tagset validation guide](tagset-validation.md).

`tokenize()` and the cached parse step use `functools.lru_cache`, so repeat calls on the same
source return the same (immutable) token tuple / AST instance.

## The three grammar layers

The parser has three expression domains with separate operator rules. Keeping them apart avoids
ambiguities and makes precedence rules explicit.

| Layer | Where it applies | Representative nodes |
|---|---|---|
| Sequence-level | Everything outside `[...]` | [`SequenceNode`][bcql_py.models.sequence.SequenceNode], [`RepetitionNode`][bcql_py.models.sequence.RepetitionNode], [`CaptureNode`][bcql_py.models.capture.CaptureNode], [`SpanQuery`][bcql_py.models.span.SpanQuery], [`RelationNode`][bcql_py.models.relation.RelationNode], [`AlignmentNode`][bcql_py.models.alignment.AlignmentNode] |
| Token-constraint | Inside `[...]` | [`AnnotationConstraint`][bcql_py.models.token.AnnotationConstraint], [`BoolConstraint`][bcql_py.models.token.BoolConstraint], [`IntegerRangeConstraint`][bcql_py.models.token.IntegerRangeConstraint] |
| Capture-constraint | After `::` | [`AnnotationRef`][bcql_py.models.capture.AnnotationRef], [`ConstraintComparison`][bcql_py.models.capture.ConstraintComparison], [`ConstraintBoolean`][bcql_py.models.capture.ConstraintBoolean] |

## The node hierarchy

All nodes inherit from [`BCQLNode`][bcql_py.models.base.BCQLNode], a frozen Pydantic
`BaseModel`. Every concrete subclass:

- has a unique `node_type: Literal[...]` discriminator;
- overrides [`to_bcql()`][bcql_py.models.base.BCQLNode.to_bcql] for lossless reconstruction;
- is immutable (`model_config = ConfigDict(frozen=True)`).

```python
from bcql_py import parse
from bcql_py.models import TokenQuery, AnnotationConstraint, StringValue

ast = parse('[word="man"]')
assert isinstance(ast, TokenQuery)
assert isinstance(ast.constraint, AnnotationConstraint)
assert isinstance(ast.constraint.value, StringValue)
ast.constraint.annotation   # 'word'
ast.constraint.value.value  # 'man'
```

See the [API reference](../api/models/index.md) for the exhaustive list.

## Traversing the AST

Because every node is a Pydantic model, a generic walker can introspect fields and recurse into
any [`BCQLNode`][bcql_py.models.base.BCQLNode]-valued attribute or list.

```python
from bcql_py import parse
from bcql_py.models import BCQLNode


def walk(node):
    """Depth-first generator yielding every BCQLNode in a tree."""
    yield node
    for field_name in type(node).model_fields:
        value = getattr(node, field_name)
        if isinstance(value, BCQLNode):
            yield from walk(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, BCQLNode):
                    yield from walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                if isinstance(item, BCQLNode):
                    yield from walk(item)


ast = parse('A:[lemma="run"]+ "fast" :: A.word != "ran"')
types = [node.node_type for node in walk(ast)]
# types includes 'global_constraint', 'sequence', 'repetition',
# 'capture', 'token_query', 'annotation_constraint', 'string_value', etc.
```

Prefer `isinstance(node, BCQLNode)` over `hasattr(node, "node_type")`: Pydantic field values that
happen to have a `node_type` attribute by coincidence will not match.

## Round-tripping

`to_bcql()` produces a string that re-parses to an `==`-equivalent AST. Every node in the library
is covered by `tests/test_roundtrip.py`.

```python
from bcql_py import parse

source = '"the" [pos="ADJ"]+ "man" within <s/>'
assert parse(parse(source).to_bcql()) == parse(source)
```

The output is not guaranteed to be *byte-identical* to the input: insignificant whitespace may be
normalised, and some brace quantifiers are canonicalised (e.g. `{0,5}` round-trips as `{,5}`).

## Custom traversal with `node_type`

For pattern-matching without `isinstance`, use `node_type`:

```python
from bcql_py import parse

ast = parse('[word="man"]')
match ast.node_type:
    case "token_query":
        print("a single token match")
    case "sequence":
        print("a sequence of tokens")
    case _:
        print("something else")
```

This is especially handy for serialised ASTs: the discriminator survives any JSON or dictionary
representation.
