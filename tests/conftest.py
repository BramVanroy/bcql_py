from pydantic import TypeAdapter

from bcql_py.models import BCQLNodeUnion
from bcql_py.parser import parse


# Single shared adapter for JSON round-trip validation. ``TypeAdapter`` over
# ``BCQLNodeUnion`` is the standard Pydantic way to (de)serialize a value
# whose type is a discriminated union rather than a single model class:
# ``BaseModel.model_validate_json`` would require us to know the concrete
# subclass up front, defeating the point of the union.
_NODE_ADAPTER: TypeAdapter[BCQLNodeUnion] = TypeAdapter(BCQLNodeUnion)


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


def json_round_trip_test(source: str):
    """Parse source, dump to JSON, validate back through the discriminated union, and check equality.

    Verifies that the AST is fully serializable and that ``BCQLNodeUnion`` can
    reconstruct the exact same tree from the JSON output. This catches both
    serialization regressions (missing fields collapsing to ``{}``) and
    discriminator regressions (wrong subclass picked on validation).

    Args:
        source (str): The BCQL query to round-trip via JSON.
    """
    node = parse(source)
    payload = node.model_dump_json()
    rebuilt = _NODE_ADAPTER.validate_json(payload)
    assert node == rebuilt, f"JSON round-trip AST mismatch for {source!r}"
    # The reconstructed tree must also reproduce the original BCQL surface form,
    # which guards against silent type-coercion losing information.
    assert node.to_bcql() == rebuilt.to_bcql(), (
        f"JSON round-trip to_bcql mismatch for {source!r}"
    )
