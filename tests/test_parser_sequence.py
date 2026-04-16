

from conftest import parse, round_trip

from bcql_py.models.sequence import RepetitionNode, SequenceNode
from bcql_py.models.token import (
    AnnotationConstraint,
    BoolConstraint,
    TokenQuery,
)


class TestSimpleSequence:
    """Adjacent tokens form a ``SequenceNode``."""

    def test_two_bare_strings(self):
        node = parse('"tall" "man"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert all(isinstance(ch, TokenQuery) for ch in node.children)

    def test_three_bare_strings(self):
        node = parse('"the" "tall" "man"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert node.children[0].shorthand.value == "the"
        assert node.children[1].shorthand.value == "tall"
        assert node.children[2].shorthand.value == "man"

    def test_single_token_no_sequence_node(self):
        """A single token should NOT produce a SequenceNode."""
        node = parse('"man"')
        assert isinstance(node, TokenQuery)

    def test_round_trip_three_words(self):
        round_trip('"the" "tall" "man"')


class TestMixedSequence:
    """Sequences mixing bare strings, bracketed queries, and match-all."""

    def test_string_and_bracket(self):
        node = parse('"an?|the" [pos="ADJ"] "man"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[0], TokenQuery)
        assert node.children[0].shorthand.value == "an?|the"
        assert isinstance(node.children[1].constraint, AnnotationConstraint)
        assert node.children[2].shorthand.value == "man"

    def test_string_matchall_string(self):
        """``"an?|the" [] "man"`` - match-all gap."""
        node = parse('"an?|the" [] "man"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert node.children[1].constraint is None

    def test_round_trip_mixed(self):
        round_trip('"an?|the" [pos="ADJ"] "man"')


class TestSequenceWithRepetition:
    """Sequences containing quantified elements."""

    def test_repetition_plus_string(self):
        """``[pos="ADJ"]+ "man"`` from the guide."""
        node = parse('[pos="ADJ"]+ "man"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], RepetitionNode)
        assert node.children[0].min_count == 1
        assert isinstance(node.children[1], TokenQuery)

    def test_brace_quantifier_in_sequence(self):
        """``[pos="ADJ"]{2,3} "man"``."""
        node = parse('[pos="ADJ"]{2,3} "man"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], RepetitionNode)
        assert node.children[0].min_count == 2
        assert node.children[0].max_count == 3

    def test_star_in_sequence(self):
        """``[pos="ADJ"]* "man"`` - zero or more."""
        node = parse('[pos="ADJ"]* "man"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], RepetitionNode)
        assert node.children[0].min_count == 0

    def test_gap_in_sequence(self):
        """``"hello" []{1,3} "world"`` - variable gap."""
        node = parse('"hello" []{1,3} "world"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], RepetitionNode)

    def test_round_trip_repetition_sequence(self):
        round_trip('[pos="ADJ"]+ "man"')

    def test_round_trip_brace_sequence(self):
        round_trip('[pos="ADJ"]{2,3} "man"')


class TestSequenceWithConstraints:
    """Sequences where tokens have compound constraints."""

    def test_bigram_with_compound_constraints(self):
        """``[word="mij"&lemma="ik"] [word="gegeven"&lemma="geven"]``."""
        node = parse('[word="mij"&lemma="ik"] [word="gegeven"&lemma="geven"]')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0].constraint, BoolConstraint)
        assert isinstance(node.children[1].constraint, BoolConstraint)

    def test_round_trip_bigram(self):
        round_trip(
            '[word="mij"&lemma="ik"] [word="gegeven"&lemma="geven"]',
            expected='[word="mij" & lemma="ik"] [word="gegeven" & lemma="geven"]',
        )

    def test_round_trip_min_only_in_sequence(self):
        round_trip('[pos="ADJ"]{2,} "man"')
