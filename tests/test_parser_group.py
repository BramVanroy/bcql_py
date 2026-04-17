"""Tests for parenthesized groups ``(...)`` and sequence-level negation ``!``.

Groups delegate back up to the lowest-precedence level, so anything valid at the top level is
valid inside parentheses. Negation sits at the span level above repetition per ``Bcql.g4``'s
``sequencePartNoCapture`` rule, so ``![pos="NOUN"]+`` parses as ``!([pos="NOUN"]+)`` rather
than ``(![pos="NOUN"]) +``.
"""

from conftest import parse, round_trip_test

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
        """``("corpus")`` - a redundant but valid parenthesized single-token query."""
        node = parse('("corpus")')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, TokenQuery)
        assert node.child.shorthand is not None
        assert node.child.shorthand.value == "corpus"

    def test_group_with_sequence(self):
        """``("in" "terminis")`` - a parenthesized two-token technical phrase."""
        node = parse('("in" "terminis")')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, SequenceNode)
        assert len(node.child.children) == 2

    def test_group_with_bracket_token(self):
        """``([word="however"])`` - parentheses around an explicit annotation constraint."""
        node = parse('([word="however"])')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, TokenQuery)
        assert isinstance(node.child.constraint, AnnotationConstraint)

    def test_nested_groups(self):
        """``(("corpus"))`` - doubly nested parentheses remain structurally visible. 
        Group nodes can be embedded indefinitely.
        """
        node = parse('(("corpus"))')
        assert isinstance(node, GroupNode)
        inner = node.child
        assert isinstance(inner, GroupNode)
        assert isinstance(inner.child, TokenQuery)

    def test_group_with_repetition(self):
        """``("in" "terminis")+`` shows repetition attaching to the whole group."""
        node = parse('("in" "terminis")+')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert node.max_count is None
        assert isinstance(node.child, GroupNode)
        assert isinstance(node.child.child, SequenceNode)

    def test_group_in_sequence(self):
        """``"the" ("United" "States") "delegation"`` embeds a grouped place name in a sequence,
        though there is no benefit of adding the parentheses here."""
        node = parse('"the" ("United" "States") "delegation"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], GroupNode)
        inner = node.children[1].child
        assert isinstance(inner, SequenceNode)
        assert len(inner.children) == 2

    def test_group_with_sequence_repetition(self):
        """``([pos="ADJ"] [pos="NOUN"]){2,3}`` repeats an adjective-noun chunk 2 to 3 times.

        The brace quantifier applies to the whole grouped phrase, not to the final token only.
        """
        node = parse('([pos="ADJ"] [pos="NOUN"]){2,3}')
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 2
        assert node.max_count == 3
        assert isinstance(node.child, GroupNode)

    def test_round_trip_single(self):
        """Round-trip: parenthesized single token preserves structure."""
        round_trip_test('("corpus")')

    def test_round_trip_sequence_group(self):
        """Round-trip: parenthesized phrase preserves structure."""
        round_trip_test('("in" "terminis")')

    def test_round_trip_group_with_repetition(self):
        """Round-trip: group with plus quantifier preserves structure."""
        round_trip_test('("in" "terminis")+')

    def test_round_trip_group_in_sequence(self):
        """Round-trip: group embedded in sequence preserves structure."""
        round_trip_test('"the" ("United" "States") "delegation"')

    def test_round_trip_nested(self):
        """Round-trip: doubly-nested parentheses preserves structure."""
        round_trip_test('(("corpus"))')


class TestNegationNode:
    """``!`` sequence-level negation."""

    def test_negate_token_query(self):
        """``![word="however"]`` negates an explicit word-form constraint."""
        node = parse('![word="however"]')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, TokenQuery)
        assert isinstance(node.child.constraint, AnnotationConstraint)
        assert node.child.constraint.annotation == "word"

    def test_negate_bare_string(self):
        """``!"however"`` negates a bare-string token query."""
        node = parse('!"however"')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, TokenQuery)
        assert node.child.shorthand is not None
        assert node.child.shorthand.value == "however"

    def test_negate_group(self):
        """``!("United" "States")`` negates a parenthesized two-token name.

        The negation applies to the entire group, not just to its first token.
        """
        node = parse('!("United" "States")')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, GroupNode)
        assert isinstance(node.child.child, SequenceNode)

    def test_negate_wraps_repetition(self):
        """``![pos="NOUN"]+`` parses as ``!([pos="NOUN"]+)`` because negation sits above repetition,
        so the example looks for a span that does not consist of one or more nouns."""
        node = parse('![pos="NOUN"]+')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, RepetitionNode)
        assert node.child.min_count == 1
        assert node.child.max_count is None
        assert isinstance(node.child.child, TokenQuery)

    def test_double_negation(self):
        """``!!"however"`` keeps the nested negation structure explicit in the AST."""
        node = parse('!!"however"')
        assert isinstance(node, NegationNode)
        assert isinstance(node.child, NegationNode)
        assert isinstance(node.child.child, TokenQuery)

    def test_negation_in_sequence(self):
        """``"the" ![pos="ADJ"] "committee"`` negates only the middle position in the sequence.

        This highlights that span-level negation still composes as one child inside a larger
        ``SequenceNode``.
        """
        node = parse('"the" ![pos="ADJ"] "committee"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], NegationNode)

    def test_round_trip_negate_token(self):
        """Round-trip: negated token query preserves structure."""
        round_trip_test('![word="however"]')

    def test_round_trip_negate_bare_string(self):
        """Round-trip: negated bare string preserves structure."""
        round_trip_test('!"however"')

    def test_round_trip_negate_group(self):
        """Round-trip: negated group preserves structure."""
        round_trip_test('!("United" "States")')

    def test_round_trip_negate_repetition(self):
        """Round-trip: negation wrapping repetition preserves structure."""
        round_trip_test('![pos="NOUN"]+')

    def test_round_trip_double_negation(self):
        """Round-trip: double negation preserves structure."""
        round_trip_test('!!"however"')

    def test_round_trip_negation_in_sequence(self):
        """Round-trip: negation in sequence preserves structure."""
        round_trip_test('"the" ![pos="ADJ"] "committee"')
