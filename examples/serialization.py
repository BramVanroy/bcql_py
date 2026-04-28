"""BCQL parsing, serialization, and round-tripping. Functionally lossless!

Demonstrates the core workflow of ``bcql_py`` serialization:
- parse a BCQL query string into a Pydantic Abstract Syntax Tree (AST)
- serialize to JSON via Pydantic
- deserialize back
- reconstruct the query string from the AST
"""

from __future__ import annotations

from bcql_py import parse


SECTION_SEPARATOR = "=" * 70


def print_section(title: str) -> None:
    """Print a clearly delimited section header.

    Args:
        title: The title to display.
    """
    print(f"\n{SECTION_SEPARATOR}\n{title}\n{SECTION_SEPARATOR}")


print_section("1. Parsing a BCQL query into an AST")

query = '"the" [pos="ADJ"]+ "man"'
print(f"Original BCQL query: {query}")
ast = parse(query)


print_section("2. Serializing the AST to JSON")

# Pydantic's ``model_dump_json`` walks the discriminated union and emits a
# ``node_type`` tag for every node, which is what makes the round-trip work.
json_str = ast.model_dump_json(indent=2)
print(json_str)


print_section("3. Deserializing JSON back into an AST")

ast2 = ast.model_validate_json(json_str)
print(f"AST equals original after round-trip: {ast == ast2}")


print_section("4. Reconstructing BCQL from the AST")

# ``to_bcql`` may differ in trivial whitespace or formatting from the original
# (for example, "up to" quantifiers are normalized), but the result is
# functionally equivalent and re-parses to the same AST.
bcql_str = ast2.to_bcql()
print(f"Reconstructed BCQL: {bcql_str}")
print(f"Identical to original string: {query == bcql_str}")
