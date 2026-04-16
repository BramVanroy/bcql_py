"""Tests for lookaround parsing (Step 12): lookahead and lookbehind assertions."""

import pytest
from conftest import parse, round_trip

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.lookaround import LookaheadNode, LookbehindNode
from bcql_py.models.sequence import SequenceNode
from bcql_py.models.token import TokenQuery


class TestLookahead:
    """Lookahead assertions: ``(?= ...)`` and ``(?! ...)``."""

    def test_positive(self):
        node = parse('(?= "cat")')
        assert isinstance(node, LookaheadNode)
        assert node.positive is True
        assert isinstance(node.body, TokenQuery)

    def test_negative(self):
        node = parse('(?! "dog")')
        assert isinstance(node, LookaheadNode)
        assert node.positive is False

    def test_complex_body(self):
        """Lookahead body can be a full constrained query."""
        node = parse('(?= [pos="N"] "cat")')
        assert isinstance(node, LookaheadNode)
        assert isinstance(node.body, SequenceNode)

    def test_in_sequence(self):
        """``"cat" (?= "sat")`` - lookahead as part of a sequence."""
        node = parse('"cat" (?= "sat")')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[1], LookaheadNode)


class TestLookbehind:
    """Lookbehind assertions: ``(?<= ...)`` and ``(?<! ...)``."""

    def test_positive(self):
        node = parse('(?<= "the")')
        assert isinstance(node, LookbehindNode)
        assert node.positive is True

    def test_negative(self):
        node = parse('(?<! "a")')
        assert isinstance(node, LookbehindNode)
        assert node.positive is False

    def test_in_sequence(self):
        """``(?<= "the") "cat"`` - lookbehind before another element."""
        node = parse('(?<= "the") "cat"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], LookbehindNode)


class TestLookaroundInContext:
    """Lookarounds combined with other constructs."""

    def test_lookahead_with_global_constraint(self):
        """Body can contain ``::`` constraints."""
        from bcql_py.models.capture import GlobalConstraintNode

        node = parse('(?= A:[pos="N"] :: A.word = "cat")')
        assert isinstance(node, LookaheadNode)
        assert isinstance(node.body, GlobalConstraintNode)

    def test_lookahead_with_repetition(self):
        """Lookahead followed by a quantifier applies repetition at span level."""
        from bcql_py.models.sequence import RepetitionNode

        node = parse('(?= "cat")+')
        assert isinstance(node, RepetitionNode)
        assert isinstance(node.child, LookaheadNode)

    def test_negated_lookahead(self):
        """``!(?= "x")`` wraps in NegationNode at span level."""
        from bcql_py.models.sequence import NegationNode

        node = parse('!(?= "x")')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, LookaheadNode)

    def test_captured_lookahead(self):
        """``A:(?= "x")`` applies capture label."""
        from bcql_py.models.capture import CaptureNode

        node = parse('A:(?= "x")')
        assert isinstance(node, CaptureNode)
        assert isinstance(node.body, LookaheadNode)


class TestRoundTrips:
    """Round-trip tests: parse -> to_bcql -> parse produces identical AST."""

    @pytest.mark.parametrize(
        "query",
        [
            '(?= "cat")',
            '(?! "dog")',
            '(?<= "the")',
            '(?<! "a")',
            '"cat" (?= "sat")',
            '(?<= "the") "cat"',
            '(?= [pos="N"] "cat")',
            '(?<= "the") (?! "a") "cat"',
            '(?= "cat")+',
            '!(?= "x")',
            'A:(?= "x")',
        ],
    )
    def test_round_trip(self, query: str):
        round_trip(query)


class TestLookaroundErrors:
    """Error cases for lookaround parsing."""

    def test_unclosed_lookahead(self):
        with pytest.raises(BCQLSyntaxError):
            parse('(?= "cat"')

    def test_empty_lookahead(self):
        """Empty body should fail (no valid atom)."""
        with pytest.raises(BCQLSyntaxError):
            parse("(?=)")

    def test_unclosed_lookbehind(self):
        with pytest.raises(BCQLSyntaxError):
            parse('(?<= "the"')
