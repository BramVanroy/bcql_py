"""Tests for repetition and quantifier parsing: ``+``, ``*``, ``?``, ``{n}``, ``{n,m}``, ``{n,}``, ``{,m}``.

The final form ``{,m}`` is a bcql_py extension: it is accepted by this parser even though it is not
present in ``Bcql.g4``.
"""

from conftest import round_trip_test

from bcql_py.models.sequence import RepetitionNode, UnderscoreNode
from bcql_py.models.token import TokenQuery
from bcql_py.parser import parse


class TestRepetitionPlus:
    """``+`` quantifier: one or more."""

    def test_plus_on_token_query(self):
        """``[pos="ADJ"]+`` - one or more consecutive adjectives."""
        node = parse('[pos="ADJ"]+')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert node.max_count is None
        assert isinstance(node.child, TokenQuery)

    def test_plus_on_bare_string(self):
        """``"very"+`` - one or more consecutive discourse intensifiers."""
        node = parse('"very"+')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert node.max_count is None

    def test_round_trip_plus(self):
        """Round-trip: one-or-more adjective quantifier preserves structure."""
        round_trip_test('[pos="ADJ"]+')


class TestRepetitionStar:
    """``*`` quantifier: zero or more."""

    def test_star_on_token_query(self):
        """``[pos="ADJ"]*`` - zero or more consecutive adjectives."""
        node = parse('[pos="ADJ"]*')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 0
        assert node.max_count is None

    def test_round_trip_star(self):
        """Round-trip: zero-or-more adjective quantifier preserves structure."""
        round_trip_test('[pos="ADJ"]*')


class TestRepetitionQuestion:
    """``?`` quantifier: zero or one."""

    def test_question_on_bare_string(self):
        """``"the"?`` - an optional determiner."""
        node = parse('"the"?')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 0
        assert node.max_count == 1

    def test_round_trip_question(self):
        """Round-trip: optional quantifier preserves structure."""
        round_trip_test('"the"?')


class TestRepetitionBrace:
    """Brace quantifiers: ``{n}``, ``{n,m}``, ``{n,}``, ``{,m}``."""

    def test_exact_count(self):
        """``[]{2}`` - match exactly 2 arbitrary tokens (a gap of 2)."""
        node = parse("[]{2}")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 2

    def test_range(self):
        """``[pos="ADJ"]{2,3}`` - 2 to 3 consecutive adjectives."""
        node = parse('[pos="ADJ"]{2,3}')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 3

    def test_min_only(self):
        """``[pos="ADJ"]{2,}`` - at least 2 consecutive adjectives, no upper bound."""
        node = parse('[pos="ADJ"]{2,}')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count is None

    def test_max_only(self):
        """``[]{,3}`` - at most 3 arbitrary tokens (bcql_py extension; not in Bcql.g4)."""
        node = parse("[]{,3}")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 0
        assert node.max_count == 3

    def test_variable_gap(self):
        """``[]{2,5}`` - a gap of 2 to 5 arbitrary tokens between other elements.

        Commonly used in sequences like ``"cause" []{2,5} "effect"`` to find "cause" and
        "effect" separated by 2 to 5 intervening words.
        """
        node = parse("[]{2,5}")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 5

    def test_round_trip_exact(self):
        """Round-trip: exact brace quantifier preserves structure."""
        round_trip_test("[]{2}")

    def test_round_trip_range(self):
        """Round-trip: range brace quantifier preserves structure."""
        round_trip_test('[pos="ADJ"]{2,3}')

    def test_round_trip_min_only(self):
        """Round-trip: min-only brace quantifier preserves structure."""
        round_trip_test('[pos="ADJ"]{2,}')

    def test_round_trip_max_only(self):
        """Round-trip: max-only brace quantifier preserves the bcql_py extension syntax."""
        round_trip_test("[]{,3}")

    def test_underscore_with_quantifier(self):
        """``_+`` - one or more relation wildcards.

        The underscore ``_`` is a wildcard for relation queries. Adding a quantifier
        is unusual but should parse correctly as a RepetitionNode wrapping an UnderscoreNode.
        """
        node = parse("_+")
        assert isinstance(node, RepetitionNode)
        assert isinstance(node.child, UnderscoreNode)
