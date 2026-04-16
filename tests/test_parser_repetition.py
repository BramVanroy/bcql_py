"""Tests for repetition/quantifier parsing: ``+``, ``*``, ``?``,
``{n}``, ``{n,m}``, ``{n,}``, ``{,m}``. Unlike bcql.g4m we do support {,m} quantifiers
"""

from conftest import parse, round_trip

from bcql_py.models.sequence import RepetitionNode, UnderscoreNode
from bcql_py.models.token import TokenQuery


class TestRepetitionPlus:
    """``+`` quantifier: one or more."""

    def test_plus_on_token_query(self):
        node = parse('[pos="ADJ"]+')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert node.max_count is None
        assert isinstance(node.child, TokenQuery)

    def test_plus_on_bare_string(self):
        node = parse('"man"+')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert node.max_count is None

    def test_round_trip_plus(self):
        round_trip('[pos="ADJ"]+')


class TestRepetitionStar:
    """``*`` quantifier: zero or more."""

    def test_star_on_token_query(self):
        node = parse('[pos="ADJ"]*')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 0
        assert node.max_count is None

    def test_round_trip_star(self):
        round_trip('[pos="ADJ"]*')


class TestRepetitionQuestion:
    """``?`` quantifier: zero or one."""

    def test_question_on_bare_string(self):
        node = parse('"word"?')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 0
        assert node.max_count == 1

    def test_round_trip_question(self):
        round_trip('"word"?')


class TestRepetitionBrace:
    """Brace quantifiers: ``{n}``, ``{n,m}``, ``{n,}``, ``{,m}``."""

    def test_exact_count(self):
        node = parse("[]{2}")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 2

    def test_range(self):
        node = parse('[pos="ADJ"]{2,3}')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 3

    def test_min_only(self):
        node = parse('[pos="ADJ"]{2,}')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count is None

    def test_max_only(self):
        node = parse("[]{,3}")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 0
        assert node.max_count == 3

    def test_variable_gap(self):
        """``[]{2,5}`` - a gap of 2 to 5 tokens."""
        node = parse("[]{2,5}")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 5

    def test_round_trip_exact(self):
        round_trip("[]{2}")

    def test_round_trip_range(self):
        round_trip('[pos="ADJ"]{2,3}')

    def test_round_trip_min_only(self):
        round_trip('[pos="ADJ"]{2,}')

    def test_round_trip_max_only(self):
        round_trip("[]{,3}")

    def test_underscore_with_quantifier(self):
        """``_`` does not normally take quantifiers, but the parser should handle it."""
        node = parse("_+")
        assert isinstance(node, RepetitionNode)
        assert isinstance(node.child, UnderscoreNode)
