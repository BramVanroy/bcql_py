"""Shared test helpers for BCQL parser tests."""

import pytest

from bcql_py.parser.lexer import BCQLLexer
from bcql_py.parser.parser import BCQLParser


def parse(source: str):
    """Lex + parse a BCQL query string and return the root AST node."""
    tokens = BCQLLexer(source).tokenize()
    return BCQLParser(tokens, source=source).parse()


def round_trip(source: str, *, expected: str | None = None):
    """Parse *source*, convert back to BCQL, and re-parse to verify stability.

    Args:
        source: The BCQL query to round-trip.
        expected: If given, assert that ``to_bcql()`` produces this exact string instead of *source*
          (useful when the parser normalises surface syntax, e.g. whitespace).
    """
    node = parse(source)
    bcql = node.to_bcql()
    expected_bcql = expected if expected is not None else source
    assert bcql == expected_bcql, f"to_bcql mismatch: {bcql!r} != {expected_bcql!r}"
    node2 = parse(bcql)
    assert node == node2, f"Round-trip AST mismatch for {source!r}"
