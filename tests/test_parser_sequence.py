from conftest import round_trip_test

from bcql_py.models.sequence import RepetitionNode, SequenceNode
from bcql_py.models.token import (
    AnnotationConstraint,
    BoolConstraint,
    TokenQuery,
)
from bcql_py.parser import parse


class TestSimpleSequence:
    """Adjacent tokens form a ``SequenceNode``."""

    def test_two_bare_strings(self):
        """``"corpus" "analysis"`` - a two-token lexical sequence."""
        node = parse('"corpus" "analysis"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert all(isinstance(ch, TokenQuery) for ch in node.children)

    def test_three_bare_strings(self):
        """``"the" "United" "States"`` - a three-token proper-name sequence."""
        node = parse('"the" "United" "States"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        for child, expected in zip(node.children, ("the", "United", "States")):
            assert isinstance(child, TokenQuery)
            assert child.shorthand is not None
            assert child.shorthand.value == expected

    def test_single_token_no_sequence_node(self):
        """``"corpus"`` - a single token stays a ``TokenQuery`` rather than becoming a sequence."""
        node = parse('"corpus"')
        assert isinstance(node, TokenQuery)

    def test_round_trip_three_words(self):
        """Round-trip: a three-token place name preserves sequence structure."""
        round_trip_test('"the" "United" "States"')


class TestMixedSequence:
    """Sequences mixing bare strings, bracketed queries, and match-all."""

    def test_string_and_bracket(self):
        """``"the" [pos="ADJ"] "analysis"`` - determiner + adjective + noun sequence.

        This reflects a common noun-phrase shape in corpora: a determiner, an adjective, and a noun.
        """
        node = parse('"the" [pos="ADJ"] "analysis"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        first, middle, last = node.children
        assert isinstance(first, TokenQuery)
        assert first.shorthand is not None
        assert first.shorthand.value == "the"
        assert isinstance(middle, TokenQuery)
        assert isinstance(middle.constraint, AnnotationConstraint)
        assert isinstance(last, TokenQuery)
        assert last.shorthand is not None
        assert last.shorthand.value == "analysis"

    def test_string_matchall_string(self):
        """``"the" [] "analysis"`` - determiner, any token, then a noun.

        The ``[]`` match-all gap can absorb any one token between the two lexical anchors.
        """
        node = parse('"the" [] "analysis"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        middle = node.children[1]
        assert isinstance(middle, TokenQuery)
        assert middle.constraint is None

    def test_round_trip_mixed(self):
        """Round-trip: mixed bare string, bracket query, and string preserves structure."""
        round_trip_test('"the" [pos="ADJ"] "analysis"')


class TestSequenceWithRepetition:
    """Sequences containing quantified elements."""

    def test_repetition_plus_string(self):
        """``[pos="ADJ"]+ "analysis"`` - one or more adjectives followed by a noun.

        The ``+`` quantifier means at least one adjective must precede the noun.
        """
        node = parse('[pos="ADJ"]+ "analysis"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], RepetitionNode)
        assert node.children[0].min_count == 1
        assert isinstance(node.children[1], TokenQuery)

    def test_brace_quantifier_in_sequence(self):
        """``[pos="ADJ"]{2,3} "analysis"`` - exactly 2 to 3 adjectives followed by a noun.

        This is a structural parser test for bounded repetition in front of a noun head.
        """
        node = parse('[pos="ADJ"]{2,3} "analysis"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], RepetitionNode)
        assert node.children[0].min_count == 2
        assert node.children[0].max_count == 3

    def test_star_in_sequence(self):
        """``[pos="ADJ"]* "analysis"`` - zero or more adjectives before a noun.

        The ``*`` quantifier allows the adjective sequence to be absent entirely.
        """
        node = parse('[pos="ADJ"]* "analysis"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], RepetitionNode)
        assert node.children[0].min_count == 0

    def test_gap_in_sequence(self):
        """``"due" []{1,3} "process"`` models a short variable-length gap in a phrase.

        The ``[]{1,3}`` gap can absorb one to three arbitrary intervening tokens.
        """
        node = parse('"due" []{1,3} "process"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], RepetitionNode)

    def test_round_trip_repetition_sequence(self):
        """Round-trip: adjective+ noun sequence preserves structure."""
        round_trip_test('[pos="ADJ"]+ "analysis"')

    def test_round_trip_brace_sequence(self):
        """Round-trip: brace quantifier in sequence preserves structure."""
        round_trip_test('[pos="ADJ"]{2,3} "analysis"')


class TestSequenceWithConstraints:
    """Sequences where tokens have compound constraints."""

    def test_bigram_with_compound_constraints(self):
        """``[word="mij"&lemma="ik"] [word="gegeven"&lemma="geven"]`` - Dutch compound bigram.

        Finds the exact two-word sequence where "mij" (me) with lemma "ik" (I) is followed by
        "gegeven" (given) with lemma "geven" (to give). This is the phrase "mij gegeven" (given
        to me) with specific lemma constraints on each word.
        """
        node = parse('[word="mij"&lemma="ik"] [word="gegeven"&lemma="geven"]')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        first, second = node.children
        assert isinstance(first, TokenQuery)
        assert isinstance(second, TokenQuery)
        assert isinstance(first.constraint, BoolConstraint)
        assert isinstance(second.constraint, BoolConstraint)

    def test_round_trip_bigram(self):
        """Round-trip: Dutch compound bigram normalises whitespace around ``&``."""
        round_trip_test(
            '[word="mij"&lemma="ik"] [word="gegeven"&lemma="geven"]',
            expected='[word="mij" & lemma="ik"] [word="gegeven" & lemma="geven"]',
        )

    def test_round_trip_min_only_in_sequence(self):
        """Round-trip: min-only brace quantifier in sequence preserves structure."""
        round_trip_test('[pos="ADJ"]{2,} "analysis"')
