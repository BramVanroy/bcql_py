"""Tests for parenthesized groups ``(...)`` and sequence-level negation ``!``.

Groups delegate back up to the lowest-precedence level (``global_cst``), so anything
valid at the top level is valid inside parentheses.  Negation sits at the span level
(above repetition) per ``Bcql.g4``'s ``sequencePartNoCapture`` rule, so ``!"man"+``
parses as ``!("man"+)`` rather than ``(!"man")+``.
"""

from conftest import parse, round_trip

from bcql_py.models.sequence import (
    GroupNode,
    NegationNode,
    RepetitionNode,
    SequenceNode,
)
from bcql_py.models.token import AnnotationConstraint, TokenQuery


class TestGroupNode:
    """``(...)`` parenthesized groups at the sequence level."""

    def test_single_token_group(self):
        node = parse('("man")')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, TokenQuery)
        assert node.child.shorthand is not None
        assert node.child.shorthand.value == "man"

    def test_group_with_sequence(self):
        node = parse('("the" "man")')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, SequenceNode)
        assert len(node.child.children) == 2

    def test_group_with_bracket_token(self):
        node = parse('([word="cat"])')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, TokenQuery)
        assert isinstance(node.child.constraint, AnnotationConstraint)

    def test_nested_groups(self):
        node = parse('(("man"))')
        assert isinstance(node, GroupNode)
        inner = node.child
        assert isinstance(inner, GroupNode)
        assert isinstance(inner.child, TokenQuery)

    def test_group_with_repetition(self):
        """``("man")+``: repetition applies to the group."""
        node = parse('("man")+')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert node.max_count is None
        assert isinstance(node.child, GroupNode)
        assert isinstance(node.child.child, TokenQuery)

    def test_group_in_sequence(self):
        """``"the" ("big" "bad") "wolf"``: group embedded in a sequence."""
        node = parse('"the" ("big" "bad") "wolf"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], GroupNode)
        inner = node.children[1].child
        assert isinstance(inner, SequenceNode)
        assert len(inner.children) == 2

    def test_group_with_sequence_repetition(self):
        """``("adj" "noun"){2,3}``: brace quantifier on a group."""
        node = parse('("adj" "noun"){2,3}')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 3
        assert isinstance(node.child, GroupNode)

    def test_round_trip_single(self):
        round_trip('("man")')

    def test_round_trip_sequence_group(self):
        round_trip('("the" "man")')

    def test_round_trip_group_with_repetition(self):
        round_trip('("man")+')

    def test_round_trip_group_in_sequence(self):
        round_trip('"the" ("big" "bad") "wolf"')

    def test_round_trip_nested(self):
        round_trip('(("man"))')


class TestNegationNode:
    """``!`` sequence-level negation."""

    def test_negate_token_query(self):
        node = parse('![word="cat"]')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, TokenQuery)
        assert isinstance(node.child.constraint, AnnotationConstraint)
        assert node.child.constraint.annotation == "word"

    def test_negate_bare_string(self):
        node = parse('!"man"')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, TokenQuery)
        assert node.child.shorthand is not None
        assert node.child.shorthand.value == "man"

    def test_negate_group(self):
        """``!("man" "woman")``: negation of a parenthesized group."""
        node = parse('!("man" "woman")')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, GroupNode)
        assert isinstance(node.child.child, SequenceNode)

    def test_negate_wraps_repetition(self):
        """``!"man"+`` parses as ``!("man"+)`` per G4: negation is at span level, above repetition."""
        node = parse('!"man"+')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, RepetitionNode)
        assert node.child.min_count == 1
        assert node.child.max_count is None
        assert isinstance(node.child.child, TokenQuery)

    def test_double_negation(self):
        node = parse('!!"man"')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, NegationNode)
        assert isinstance(node.child.child, TokenQuery)

    def test_negation_in_sequence(self):
        """``"the" ![pos="adj"] "dog"``: negation within a sequence."""
        node = parse('"the" ![pos="adj"] "dog"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], NegationNode)

    def test_round_trip_negate_token(self):
        round_trip('![word="cat"]')

    def test_round_trip_negate_bare_string(self):
        round_trip('!"man"')

    def test_round_trip_negate_group(self):
        round_trip('!("man" "woman")')

    def test_round_trip_negate_repetition(self):
        round_trip('!"man"+')

    def test_round_trip_double_negation(self):
        round_trip('!!"man"')

    def test_round_trip_negation_in_sequence(self):
        round_trip('"the" ![pos="adj"] "dog"')
