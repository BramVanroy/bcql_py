"""Tests for capture labels: ``IDENT ':' body``.

Per ``Bcql.g4``'s ``captureQuery: (captureLabel ':')* sequencePartNoCapture``, captures support
multiple chained labels such as ``head:focus:[word="however"]``. Chained labels nest rather than
forming a flat list. Captures bind tighter than sequence juxtaposition but looser than the span-
level operators wrapped by ``sequencePartNoCapture``.
"""

from conftest import parse, round_trip_test

from bcql_py.models import UnderscoreNode
from bcql_py.models.capture import CaptureNode
from bcql_py.models.sequence import (
    GroupNode,
    NegationNode,
    RepetitionNode,
    SequenceBoolNode,
    SequenceNode,
)
from bcql_py.models.token import AnnotationConstraint, TokenQuery


class TestCaptureBasic:
    """Basic ``label:body`` capture syntax."""

    def test_capture_bracket_token(self):
        """``A:[pos="ADJ"]`` - capture an adjective token under the label "A"."""
        node = parse('A:[pos="ADJ"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, TokenQuery)
        assert isinstance(node.body.constraint, AnnotationConstraint)
        assert node.body.constraint.annotation == "pos"
        assert node.body.constraint.value.value == "ADJ"

    def test_capture_bare_string(self):
        """``head:"corpus"`` captures a lexical token under a descriptive label."""
        node = parse('head:"corpus"')
        assert isinstance(node, CaptureNode)
        assert node.label == "head"
        assert isinstance(node.body, TokenQuery)
        assert node.body.shorthand is not None
        assert node.body.shorthand.value == "corpus"

    def test_capture_underscore(self):
        """``token:_`` captures any single token under a descriptive label."""
        node = parse("token:_")
        assert isinstance(node, CaptureNode)
        assert node.label == "token"
        assert isinstance(node.body, UnderscoreNode)

    def test_capture_empty_brackets(self):
        """``token:[]`` captures any token via the match-all pattern."""
        node = parse("token:[]")
        assert isinstance(node, CaptureNode)
        assert node.label == "token"
        assert isinstance(node.body, TokenQuery)
        assert node.body.constraint is None

    def test_capture_long_label(self):
        """``adjectives:[pos="ADJ"]`` - descriptive label names are allowed.

        Label names can be any identifier, not just single letters. This makes global
        constraints more readable: ``adjectives:[pos="ADJ"] :: adjectives.word = "big"``.
        """
        node = parse('adjectives:[pos="ADJ"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "adjectives"

    def test_round_trip_capture_token(self):
        """Round-trip: capture with bracket token preserves structure."""
        round_trip_test('A:[pos="ADJ"]')

    def test_round_trip_capture_string(self):
        """Round-trip: capture with bare string preserves structure."""
        round_trip_test('head:"corpus"')

    def test_round_trip_capture_underscore(self):
        """Round-trip: capture with underscore wildcard preserves structure."""
        round_trip_test("token:_")

    def test_round_trip_capture_empty(self):
        """Round-trip: capture with match-all token preserves structure."""
        round_trip_test("token:[]")


class TestCaptureChained:
    """Multiple chained labels: ``A:B:body``."""

    def test_two_labels(self):
        """``head:focus:[word="however"]`` - two chained labels on one token.

        Chained labels nest as separate ``CaptureNode`` wrappers so both labels can be referenced
        later in global constraints.

        NOTE: I am not sure what the use-case for this is...

        Assignment `:` is right-associative, so the parse is `head:(focus:[word="however"])`
        """
        node = parse('head:focus:[word="however"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "head"
        assert isinstance(node.body, CaptureNode)
        assert node.body.label == "focus"
        assert isinstance(node.body.body, TokenQuery)

    def test_three_labels(self):
        """``clause:head:focus:"however"`` nests three labels around one token query."""
        node = parse('clause:head:focus:"however"')
        assert isinstance(node, CaptureNode)
        assert node.label == "clause"
        inner = node.body
        assert isinstance(inner, CaptureNode)
        assert inner.label == "head"
        inner2 = inner.body
        assert isinstance(inner2, CaptureNode)
        assert inner2.label == "focus"
        assert isinstance(inner2.body, TokenQuery)

    def test_round_trip_two_labels(self):
        """Round-trip: chained capture labels preserve structure."""
        round_trip_test('head:focus:[word="however"]')


class TestCaptureInSequence:
    """Captures within sequences."""

    def test_capture_in_sequence(self):
        """``modifier:[pos="ADJ"] "analysis"`` captures an adjective before a noun.

        Only the first token is captured; the following noun remains uncaptured.
        """
        node = parse('modifier:[pos="ADJ"] "analysis"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], CaptureNode)
        assert node.children[0].label == "modifier"
        assert isinstance(node.children[1], TokenQuery)

    def test_multiple_captures_in_sequence(self):
        """``pastry:[] "by" baker:[]`` captures both sides of an English by-phrase.

        This is a realistic shape for passive constructions such as ``written by Shakespeare``.
        """
        node = parse('pastry:[] "by" baker:[]')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[0], CaptureNode)
        assert node.children[0].label == "pastry"
        assert isinstance(node.children[2], CaptureNode)
        assert node.children[2].label == "baker"

    def test_round_trip_capture_in_sequence(self):
        """Round-trip: capture in sequence preserves structure."""
        round_trip_test('modifier:[pos="ADJ"] "analysis"')

    def test_round_trip_multiple_captures(self):
        """Round-trip: multiple captures in sequence preserves structure."""
        round_trip_test('pastry:[] "by" baker:[]')


class TestCaptureWithRepetition:
    """Capture interacts with repetition and groups."""

    def test_capture_with_repetition(self):
        """``A:[pos="ADJ"]+``: repetition applies to the body, not the capture itself.
        Since capture is above span in precedence, ``A:X+`` means ``A:(X+)``
        
        That means ``A`` captures the full span of one or more adjectives, not just a single adjective token.
        """
        node = parse('A:[pos="ADJ"]+')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, RepetitionNode)
        assert node.body.min_count == 1
        assert isinstance(node.body.child, TokenQuery)

    def test_capture_group(self):
        """``phrase:("in" "terminis")`` captures a grouped two-token phrase."""
        node = parse('phrase:("in" "terminis")')
        assert isinstance(node, CaptureNode)
        assert node.label == "phrase"
        assert isinstance(node.body, GroupNode)
        assert isinstance(node.body.child, SequenceNode)

    def test_capture_negation(self):
        """``focus:![pos="ADJ"]`` captures a token that is explicitly not tagged as an adjective."""
        node = parse('focus:![pos="ADJ"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "focus"
        assert isinstance(node.body, NegationNode)

    def test_round_trip_capture_repetition(self):
        """Round-trip: capture with repetition preserves structure."""
        round_trip_test('A:[pos="ADJ"]+')

    def test_round_trip_capture_group(self):
        """Round-trip: capture group preserves structure."""
        round_trip_test('phrase:("in" "terminis")')

    def test_round_trip_capture_negation(self):
        """Round-trip: capture negation preserves structure."""
        round_trip_test('focus:![pos="ADJ"]')


class TestCaptureWithBoolOps:
    """Captures in boolean expressions."""

    def test_capture_in_union(self):
        """``left:"however" | right:"therefore"`` captures each side of a lexical alternative.

        NOTE: This makes it possible for later constraints to know which alternative branch matched, though
        I'm curious how people would actually use this. Maybe in global constraints, like
        ``left:"baker" | right:"bake" :: left.pos = "N" | right.pos = "V"``

        which would be a roundabout way of writing ``[word="baker" & pos="N"] | [word="bake" & pos="V"]``
        """
        node = parse('left:"however" | right:"therefore"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, CaptureNode)
        assert node.left.label == "left"
        assert isinstance(node.right, CaptureNode)
        assert node.right.label == "right"

    def test_round_trip_capture_in_union(self):
        """Round-trip: captures in union preserves structure."""
        round_trip_test('left:"however" | right:"therefore"')
