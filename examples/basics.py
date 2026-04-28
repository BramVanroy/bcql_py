"""Basic BCQL parsing and AST walking example.

Walks through the core methods of ``bcql_py``:
- ``tokenize``: lexing a query into tokens
- ``parse``: turning that token stream into a Pydantic Abstract Syntax Tree
- inspecting AST nodes via their typed fields and ``node_type`` discriminator
- traversing the AST depth-first and breadth-first
- ``to_bcql`` / ``bcql``: reconstructing the query string from any subtree
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterator

from bcql_py import parse, tokenize
from bcql_py.models import BCQLNode, TokenQuery


SECTION_SEPARATOR = "=" * 70


def print_section(title: str) -> None:
    """Print a clearly delimited section header.

    Args:
        title: The title to display.
    """
    print(f"\n{SECTION_SEPARATOR}\n{title}\n{SECTION_SEPARATOR}")


def iter_children(node: BCQLNode) -> Iterator[BCQLNode]:
    """Yield every direct child :class:`BCQLNode` of ``node``.

    Mirrors what the validator does internally: walks each typed Pydantic field
    and expands lists/dicts. Useful for hand-rolled tree traversal.

    `type(node).model_fields` allows us to find the exact Node type's
    fields without needing to hardcode them or worry about inheritance.

    Args:
        node: The AST node whose direct children should be yielded.
    """
    for field_name in type(node).model_fields:
        value = getattr(node, field_name)
        yield from _walk_value(value)


def _walk_value(value: object) -> Iterator[BCQLNode]:
    """Recursion, yay!"""
    if isinstance(value, BCQLNode):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_value(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_value(item)


def walk_depth_first(root: BCQLNode) -> Iterator[BCQLNode]:
    """Yield every node in ``root`` in depth-first order, following
    field order of each node.

    Args:
        root: The AST root to traverse.
    """
    yield root
    for child in iter_children(root):
        yield from walk_depth_first(child)


def walk_breadth_first(root: BCQLNode) -> Iterator[BCQLNode]:
    """Yield every node in ``root`` level-by-level (root, then its children, etc.).

    Args:
        root: The AST root to traverse.
    """
    queue: deque[BCQLNode] = deque([root])
    while queue:
        node = queue.popleft()
        yield node
        queue.extend(iter_children(node))


print_section("1. Tokenizing a query")

query = '"the" [pos="ADJ"]+ "man"'
print(f"Query: {query}")
tokens = tokenize(query)
print(f"\nLexer produced {len(tokens)} tokens:")
for token in tokens:
    print(f"  {token}")


print_section("2. Parsing into an AST")

ast = parse(query)
print(f"Root node type: {ast.node_type} ({type(ast).__name__})")
print("\nPretty-printed AST (Pydantic model_dump):")
print(json.dumps(ast.model_dump(), indent=2))


print_section("3. Inspecting fields on a single node")

# The root for this query is a SequenceNode with three children.
print(f"Root has {len(ast.children)} children:")
for idx, child in enumerate(ast.children):
    print(f"  [{idx}] node_type={child.node_type!r} -> {child.to_bcql()!r}")

# Each node's bcql representation can be obtained via to_bcql() or the cached
# ``.bcql`` property, which is handy when printing nested structures.
print(f"\nRoot .bcql (cached property): {ast.bcql!r}")


print_section("4. Depth-first traversal")

print("Visiting every node in pre-order:")
for node in walk_depth_first(ast):
    print(f"  {node.node_type:25s} -> {node.bcql}")


print_section("5. Breadth-first traversal")

print("Visiting every node level-by-level:")
for node in walk_breadth_first(ast):
    print(f"  {node.node_type:25s} -> {node.bcql}")


print_section("6. Filtering nodes by type")

token_queries = [n for n in walk_depth_first(ast) if isinstance(n, TokenQuery)]
print(f"Found {len(token_queries)} TokenQuery nodes:")
for token_query in token_queries:
    if token_query.shorthand is not None:
        print(f"  shorthand string -> {token_query.shorthand.value!r}")
    elif token_query.constraint is not None:
        print(f"  bracketed        -> {token_query.constraint.bcql}")
    else:
        print("  match-all []")


print_section("7. Reconstructing BCQL from any subtree")

# Every node in the tree has its own to_bcql(), so you can render either the
# whole query or just a sub-expression. This is useful for debugging or for
# building tooling that quotes parts of a query back at the user.
print(f"Whole query   -> {ast.to_bcql()}")
print(f"First child   -> {ast.children[0].to_bcql()}")
print(f"Middle child  -> {ast.children[1].to_bcql()}")


print_section("8. A more complex query")

complex_query = 'a:[pos="DET"] b:[pos="ADJ"]+ c:[pos="NOUN"] :: a.word = "the"'
print(f"Query: {complex_query}")
complex_ast = parse(complex_query)

# Just count nodes by type to give a feel for the shape of the AST.
counts: dict[str, int] = {}
for node in walk_depth_first(complex_ast):
    counts[node.node_type] = counts.get(node.node_type, 0) + 1

print("\nNode type counts:")
for node_type, count in sorted(counts.items(), key=lambda item: -item[1]):
    print(f"  {node_type:30s} {count}")

print(f"\nReconstructed: {complex_ast.to_bcql()}")
