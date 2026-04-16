"""Tests for capture labels: ``IDENT ':' body``.

Per ``Bcql.g4``'s ``captureQuery: (captureLabel ':')* sequencePartNoCapture``,
captures support multiple chained labels (e.g. ``A:B:[word="cat"]``).
Captures bind tighter than sequence juxtaposition but looser than spans.
"""

from conftest import parse, round_trip

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
        """``A:[pos="ADJ"]``: capture a token query."""
        node = parse('A:[pos="ADJ"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, TokenQuery)
        assert isinstance(node.body.constraint, AnnotationConstraint)
        assert node.body.constraint.annotation == "pos"

    def test_capture_bare_string(self):
        """``A:"man"``: capture a bare string."""
        node = parse('A:"man"')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, TokenQuery)
        assert node.body.shorthand is not None
        assert node.body.shorthand.value == "man"

    def test_capture_underscore(self):
        """``A:_``: capture an underscore wildcard."""
        node = parse("A:_")
        assert isinstance(node, CaptureNode)
        assert node.label == "A"

    def test_capture_empty_brackets(self):
        """``A:[]``: capture match-all."""
        node = parse("A:[]")
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, TokenQuery)
        assert node.body.constraint is None

    def test_capture_long_label(self):
        """``adjectives:[pos="ADJ"]``: longer label name."""
        node = parse('adjectives:[pos="ADJ"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "adjectives"

    def test_round_trip_capture_token(self):
        round_trip('A:[pos="ADJ"]')

    def test_round_trip_capture_string(self):
        round_trip('A:"man"')

    def test_round_trip_capture_underscore(self):
        round_trip("A:_")

    def test_round_trip_capture_empty(self):
        round_trip("A:[]")


class TestCaptureChained:
    """Multiple chained labels: ``A:B:body``."""

    def test_two_labels(self):
        """``A:B:[word="cat"]``: two labels on one token."""
        node = parse('A:B:[word="cat"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, CaptureNode)
        assert node.body.label == "B"
        assert isinstance(node.body.body, TokenQuery)

    def test_three_labels(self):
        """``A:B:C:"word"``."""
        node = parse('A:B:C:"word"')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        inner = node.body
        assert isinstance(inner, CaptureNode)
        assert inner.label == "B"
        inner2 = inner.body
        assert isinstance(inner2, CaptureNode)
        assert inner2.label == "C"
        assert isinstance(inner2.body, TokenQuery)

    def test_round_trip_two_labels(self):
        round_trip('A:B:[word="cat"]')


class TestCaptureInSequence:
    """Captures within sequences."""

    def test_capture_in_sequence(self):
        """``A:[pos="ADJ"] "man"``: capture as part of a sequence."""
        node = parse('A:[pos="ADJ"] "man"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], CaptureNode)
        assert node.children[0].label == "A"
        assert isinstance(node.children[1], TokenQuery)

    def test_multiple_captures_in_sequence(self):
        """``A:[] "by" B:[]``: two captures in sequence."""
        node = parse('A:[] "by" B:[]')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[0], CaptureNode)
        assert node.children[0].label == "A"
        assert isinstance(node.children[2], CaptureNode)
        assert node.children[2].label == "B"

    def test_round_trip_capture_in_sequence(self):
        round_trip('A:[pos="ADJ"] "man"')

    def test_round_trip_multiple_captures(self):
        round_trip('A:[] "by" B:[]')


class TestCaptureWithRepetition:
    """Capture interacts with repetition and groups."""

    def test_capture_with_repetition(self):
        """``A:[pos="ADJ"]+``: repetition applies to the body, not the capture itself.
        Since capture is above span in precedence, ``A:X+`` means ``A:(X+)``.
        """
        node = parse('A:[pos="ADJ"]+')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, RepetitionNode)
        assert node.body.min_count == 1
        assert isinstance(node.body.child, TokenQuery)

    def test_capture_group(self):
        """``A:("big" "bad")``: capture a parenthesized group."""
        node = parse('A:("big" "bad")')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, GroupNode)
        assert isinstance(node.body.child, SequenceNode)

    def test_capture_negation(self):
        """``A:![pos="ADJ"]``: capture a negated token."""
        node = parse('A:![pos="ADJ"]')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, NegationNode)

    def test_round_trip_capture_repetition(self):
        round_trip('A:[pos="ADJ"]+')

    def test_round_trip_capture_group(self):
        round_trip('A:("big" "bad")')

    def test_round_trip_capture_negation(self):
        round_trip('A:![pos="ADJ"]')


class TestCaptureWithBoolOps:
    """Captures in boolean expressions."""

    def test_capture_in_union(self):
        """``A:"cat" | B:"dog"``: captures inside union alternatives."""
        node = parse('A:"cat" | B:"dog"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, CaptureNode)
        assert node.left.label == "A"
        assert isinstance(node.right, CaptureNode)
        assert node.right.label == "B"

    def test_round_trip_capture_in_union(self):
        round_trip('A:"cat" | B:"dog"')
