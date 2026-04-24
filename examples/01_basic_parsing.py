"""Basic BCQL parsing, serialization, and round-tripping.

Demonstrates the core workflow of ``bcql_py``: parse a BCQL query string into a Pydantic
Abstract Syntax Tree (AST), serialize to JSON via Pydantic, deserialize back, and reconstruct
the query.
"""

from bcql_py import parse


# Parse a simple token query
ast = parse('[word="man"]')
print("Parsed AST type:", type(ast).__name__)
print("BCQL round-trip:", ast.to_bcql())
# -> [word="man"]

# Shorthand notation
ast = parse('"man"')
print("\nShorthand:", ast.to_bcql())
# -> "man"  (equivalent to [word="man"])

# Sequence of tokens
ast = parse('"the" [pos="ADJ"]+ "man"')
print("\nSequence:", ast.to_bcql())
# -> "the" [pos="ADJ"]+ "man"

# Boolean constraints inside a token
ast = parse('[lemma="search" & pos="noun"]')
print("\nBoolean:", ast.to_bcql())
# -> [lemma="search" & pos="noun"]

# JSON serialization and deserialization via Pydantic
ast = parse('[pos="ADJ"]')
json_str = ast.model_dump_json(indent=2)
print("\nJSON representation:")
print(json_str)

# Deserialize back into the same concrete node class
ast2 = type(ast).model_validate_json(json_str)
print("\nDeserialized round-trip:", ast2.to_bcql())
assert ast == ast2, "Round-trip should produce equal ASTs"
print("Round-trip equality: OK")
