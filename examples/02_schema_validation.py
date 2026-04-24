"""Tokenization and AST inspection.

Demonstrates the lower-level ``tokenize`` and ``parse_from_tokens`` entry points and
how to inspect the resulting AST. Corpus-schema validation (restricting annotation
names / values) is not yet implemented in ``bcql_py``: see the TODO in README.md.
"""

from bcql_py import parse, parse_from_tokens, tokenize
from bcql_py.models import AnnotationConstraint, SequenceNode, TokenQuery


# Tokenize a query into its lexical tokens
tokens = tokenize('"the" [pos="ADJ"]+ "man"')
print("=== Tokenize ===")
for token in tokens:
    print(f"  {token}")

# Parse from a pre-tokenized stream (useful for custom pipelines)
source = '"the" [pos="ADJ"]+ "man"'
ast = parse_from_tokens(tokenize(source), source=source)
print(f"\nparse_from_tokens result: {ast.to_bcql()}")

# Inspecting concrete AST nodes
print("\n=== AST inspection ===")
ast = parse('[lemma="search" & pos="noun"]')
print(f"Root node type: {type(ast).__name__}")
assert isinstance(ast, TokenQuery)
print(f"  negated: {ast.negated}")
print(f"  constraint type: {type(ast.constraint).__name__}")

# Walking a sequence
ast = parse('"the" [pos="ADJ"] "man"')
assert isinstance(ast, SequenceNode)
print("\nSequence children:")
for child in ast.children:
    print(f"  {type(child).__name__}: {child.to_bcql()}")

# Drilling into an annotation constraint
ast = parse('[pos="NOUN"]')
assert isinstance(ast, TokenQuery)
constraint = ast.constraint
assert isinstance(constraint, AnnotationConstraint)
print("\nAnnotation constraint:")
print(f"  annotation: {constraint.annotation}")
print(f"  operator:   {constraint.operator}")
print(f"  value:      {constraint.value.value}")
