"""Tests for sequence-level "boolean" operators ``|``, ``&``, and ``->``.

Per ``Bcql.g4``'s ``booleanOperator`` rule, all three share the same precedence
and are left-associative. Boolean operators bind looser than juxtaposition
(sequence), so ``"a" "b" | "c" "d"`` is ``("a" "b") | ("c" "d")``.
"""

from conftest import parse, round_trip

from bcql_py.models.sequence import (
    GroupNode,
    NegationNode,
    RepetitionNode,
    SequenceBoolNode,
    SequenceNode,
)
from bcql_py.models.token import AnnotationConstraint, TokenQuery


class TestSequenceUnion:
    """``|`` at the sequence level."""

    def test_simple_union(self):
        node = parse('"cat" | "dog"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, TokenQuery)
        assert node.left.shorthand is not None
        assert node.left.shorthand.value == "cat"
        assert node.right.shorthand is not None
        assert node.right.shorthand.value == "dog"

    def test_union_with_sequences(self):
        """``"a" "b" | "c" "d"`` -> ``("a" "b") | ("c" "d")``."""
        node = parse('"a" "b" | "c" "d"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceNode)
        assert len(node.left.children) == 2
        assert isinstance(node.right, SequenceNode)
        assert len(node.right.children) == 2

    def test_three_way_union_left_assoc(self):
        """``"a" | "b" | "c"`` -> ``("a" | "b") | "c"``."""
        node = parse('"a" | "b" | "c"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "|"
        assert isinstance(node.right, TokenQuery)

    def test_round_trip_union(self):
        round_trip('"cat" | "dog"')

    def test_round_trip_union_sequences(self):
        round_trip('"a" "b" | "c" "d"')

    def test_round_trip_three_way(self):
        round_trip('"a" | "b" | "c"')


class TestSequenceIntersection:
    """``&`` at the sequence level."""

    def test_simple_intersection(self):
        # ``"double" [] & [] "trouble"``: intersection of two sequences with match-all gap.
        # Effectively the same as "double" "trouble" but intended to show how intersection
        # of queries works.
        node = parse('"double" [] & [] "trouble"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "&"
        assert isinstance(node.left, SequenceNode)
        assert isinstance(node.right, SequenceNode)

    def test_round_trip_intersection(self):
        round_trip('"double" [] & [] "trouble"')


class TestSequenceImplication:
    """``->`` implication at the sequence level."""

    def test_simple_implication(self):
        node = parse('"a" -> "b"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "->"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, TokenQuery)

    def test_round_trip_implication(self):
        round_trip('"a" -> "b"')


class TestMixedBoolOperators:
    """Mixed ``&``, ``|``, ``->`` at same precedence level."""

    def test_union_then_intersection(self):
        """``"a" | "b" & "c"`` -> ``("a" | "b") & "c"`` (left-assoc, same prec)."""
        node = parse('"a" | "b" & "c"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "&"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "|"
        assert isinstance(node.right, TokenQuery)

    def test_intersection_then_union(self):
        """``"a" & "b" | "c"`` -> ``("a" & "b") | "c"``."""
        node = parse('"a" & "b" | "c"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "&"

    def test_implication_mixed(self):
        """``"a" -> "b" | "c"`` -> ``("a" -> "b") | "c"``."""
        node = parse('"a" -> "b" | "c"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "->"

    def test_round_trip_mixed_union_intersection(self):
        round_trip('"a" | "b" & "c"')

    def test_round_trip_mixed_implication(self):
        round_trip('"a" -> "b" | "c"')


class TestBoolWithGroups:
    """Boolean operators interact with groups and negation."""

    def test_group_overrides_precedence(self):
        """``"a" | ("b" & "c")`` - parens force ``&`` to bind tighter."""
        node = parse('"a" | ("b" & "c")')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, GroupNode)
        inner = node.right.child
        assert isinstance(inner, SequenceBoolNode)
        assert inner.operator == "&"

    def test_union_with_bracket_tokens(self):
        node = parse('[word="cat"] | [word="dog"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        left = node.left
        assert isinstance(left, TokenQuery)
        assert isinstance(left.constraint, AnnotationConstraint)
        assert left.constraint.annotation == "word"

    def test_negation_inside_union(self):
        """``!"a" | "b"``: negation binds tighter than ``|``."""
        node = parse('!"a" | "b"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, NegationNode)
        assert isinstance(node.right, TokenQuery)

    def test_repetition_inside_union(self):
        """``"a"+ | "b"*``: repetition binds tighter than ``|``."""
        node = parse('"a"+ | "b"*')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, RepetitionNode)
        assert isinstance(node.right, RepetitionNode)

    def test_round_trip_group_overrides(self):
        round_trip('"a" | ("b" & "c")')

    def test_round_trip_bracket_union(self):
        round_trip('[word="cat"] | [word="dog"]')

    def test_round_trip_negation_in_union(self):
        round_trip('!"a" | "b"')

    def test_round_trip_repetition_in_union(self):
        round_trip('"a"+ | "b"*')
