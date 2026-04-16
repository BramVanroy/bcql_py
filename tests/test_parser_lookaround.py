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
        """``(?= [pos="NOUN"])`` - assert that a noun follows without consuming it."""
        node = parse('(?= [pos="NOUN"])')
        assert isinstance(node, LookaheadNode)
        assert node.positive is True
        assert isinstance(node.body, TokenQuery)

    def test_negative(self):
        """``(?! [pos="PUNCT"])`` - assert that punctuation does not follow."""
        node = parse('(?! [pos="PUNCT"])')
        assert isinstance(node, LookaheadNode)
        assert node.positive is False

    def test_complex_body(self):
        """``(?= [pos="DET"] [pos="NOUN"])`` - lookahead with a multi-token body.

        The lookahead body can itself be a full sequence query.
        """
        node = parse('(?= [pos="DET"] [pos="NOUN"])')
        assert isinstance(node, LookaheadNode)
        assert isinstance(node.body, SequenceNode)

    def test_in_sequence(self):
        """``[lemma="analysis"] (?= [lemma="show"])`` asserts right context inside a sequence.

        The lookahead does not consume tokens; only the left token is part of the actual match.
        """
        node = parse('[lemma="analysis"] (?= [lemma="show"])')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[1], LookaheadNode)


class TestLookbehind:
    """Lookbehind assertions: ``(?<= ...)`` and ``(?<! ...)``."""

    def test_positive(self):
        """``(?<= [pos="DET"])`` - assert that a determiner occurs immediately before the position."""
        node = parse('(?<= [pos="DET"])')
        assert isinstance(node, LookbehindNode)
        assert node.positive is True

    def test_negative(self):
        """``(?<! [pos="DET"])`` - assert that a determiner does not occur immediately before."""
        node = parse('(?<! [pos="DET"])')
        assert isinstance(node, LookbehindNode)
        assert node.positive is False

    def test_in_sequence(self):
        """``(?<= [pos="DET"]) [pos="NOUN"]`` finds nouns only when preceded by a determiner.

        The lookbehind asserts left context without consuming it.
        """
        node = parse('(?<= [pos="DET"]) [pos="NOUN"]')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], LookbehindNode)


class TestLookaroundInContext:
    """Lookarounds combined with other constructs."""

    def test_lookahead_with_global_constraint(self):
        """``(?= head:[pos="NOUN"] :: head.lemma = "analysis")`` - lookahead body with a global constraint.

        The lookahead body is not restricted to plain tokens; it can be any constrained query.
        """
        from bcql_py.models.capture import GlobalConstraintNode

        node = parse('(?= head:[pos="NOUN"] :: head.lemma = "analysis")')
        assert isinstance(node, LookaheadNode)
        assert isinstance(node.body, GlobalConstraintNode)

    def test_lookahead_with_repetition(self):
        """``(?= [pos="NOUN"])+`` - repetition applies to the lookahead node at span level.

        Unusual but syntactically valid: the quantifier wraps the lookahead node.
        """
        from bcql_py.models.sequence import RepetitionNode

        node = parse('(?= [pos="NOUN"])+')
        assert isinstance(node, RepetitionNode)
        assert isinstance(node.child, LookaheadNode)

    def test_negated_lookahead(self):
        """``!(?= [pos="PUNCT"])`` - span-level negation wrapping a positive lookahead.

        Different from negative lookahead ``(?! [pos="PUNCT"])``: this negates the entire lookahead
        node at the span level.
        """
        from bcql_py.models.sequence import NegationNode

        node = parse('!(?= [pos="PUNCT"])')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, LookaheadNode)

    def test_captured_lookahead(self):
        """``context:(?= [pos="NOUN"])`` applies a capture label to a lookahead assertion."""
        from bcql_py.models.capture import CaptureNode

        node = parse('context:(?= [pos="NOUN"])')
        assert isinstance(node, CaptureNode)
        assert isinstance(node.body, LookaheadNode)


class TestRoundTrips:
    """Round-trip tests: parse -> to_bcql -> parse produces identical AST."""

    @pytest.mark.parametrize(
        "query",
        [
            '(?= [pos="NOUN"])',
            '(?! [pos="PUNCT"])',
            '(?<= [pos="DET"])',
            '(?<! [pos="DET"])',
            '[lemma="analysis"] (?= [lemma="show"])',
            '(?<= [pos="DET"]) [pos="NOUN"]',
            '(?= [pos="DET"] [pos="NOUN"])',
            '(?<= [pos="DET"]) (?! [pos="PUNCT"]) [pos="NOUN"]',
            '(?= [pos="NOUN"])+',
            '!(?= [pos="PUNCT"])',
            'context:(?= [pos="NOUN"])',
        ],
    )
    def test_round_trip(self, query: str):
        round_trip(query)


class TestLookaroundErrors:
    """Error cases for lookaround parsing."""

    def test_unclosed_lookahead(self):
        """``(?= [pos="NOUN"]`` - missing closing parenthesis should error."""
        with pytest.raises(BCQLSyntaxError):
            parse('(?= [pos="NOUN"]')

    def test_empty_lookahead(self):
        """``(?=)`` - empty lookahead body should error."""
        with pytest.raises(BCQLSyntaxError):
            parse("(?=)")

    def test_unclosed_lookbehind(self):
        """``(?<= [pos="DET"]`` - missing closing parenthesis should error."""
        with pytest.raises(BCQLSyntaxError):
            parse('(?<= [pos="DET"]')
