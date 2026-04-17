from __future__ import annotations

from bcql_py.parser import parse


def round_trip_test(source: str, *, expected: str | None = None):
    """Parse source, convert back to BCQL, and re-parse to verify stability.

    Args:
        source (str): The BCQL query to round-trip.
        expected (str | None): If given, assert that ``to_bcql()`` produces this exact string instead of *source*
          (useful when the parser normalises surface syntax, e.g. whitespace).
    """
    node = parse(source)
    bcql = node.to_bcql()
    if expected is not None:
        assert bcql == expected, f"to_bcql mismatch: {bcql!r} != {expected!r}"
    node2 = parse(bcql)
    assert node == node2, f"Round-trip AST mismatch for {source!r}"
