"""Tests for position-filter operators: ``within``, ``containing``, and ``overlap``.

These operators are right-recursive in the grammar, so chained filters parse from right to left.
They also bind looser than sequence-level boolean operators.
"""

from conftest import parse, round_trip

from bcql_py.models.sequence import GroupNode, SequenceBoolNode, SequenceNode
from bcql_py.models.span import PositionFilterNode, SpanQuery
from bcql_py.models.token import TokenQuery


class TestWithin:
    """The ``within`` operator filters hits that occur inside a span."""

    def test_token_within_span(self):
        """``"baker" within <person/>`` - find the word "baker" only when it occurs inside a person-name span.

        Without the filter, "baker" also matches the occupation. The ``within`` operator restricts
        hits to those occurring inside the given span.
        """
        node = parse('"baker" within <person/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, SpanQuery)
        assert node.right.tag_name == "person"

    def test_sequence_within_span(self):
        """``"the" "committee" within <np/>`` keeps the whole phrase on the left of ``within``."""
        node = parse('"the" "committee" within <np/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, SequenceNode)
        assert isinstance(node.right, SpanQuery)

    def test_token_within_token(self):
        """``[pos="NNP"] within [word="Baker"]`` - filter can use any query on both sides."""
        node = parse('[pos="NNP"] within [word="Baker"]')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"

    def test_within_round_trip(self):
        """Round-trip: within filter preserves structure."""
        round_trip('"baker" within <person/>')

    def test_within_sequence_round_trip(self):
        """Round-trip: sequence within span preserves structure."""
        round_trip('"the" "committee" within <np/>')


class TestContaining:
    """The ``containing`` operator filters spans that contain a hit."""

    def test_span_containing_token(self):
        """``<s/> containing "however"`` - find sentences that contain the discourse marker ``however``."""
        node = parse('<s/> containing "however"')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "containing"
        assert isinstance(node.left, SpanQuery)
        assert isinstance(node.right, TokenQuery)

    def test_containing_round_trip(self):
        """Round-trip: containing filter preserves structure."""
        round_trip('<s/> containing "however"')


class TestOverlap:
    """The ``overlap`` operator matches positions where two queries overlap."""

    def test_basic_overlap(self):
        """``<np/> overlap <vp/>`` - find positions where a noun phrase and verb phrase overlap."""
        node = parse("<np/> overlap <vp/>")
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "overlap"
        assert isinstance(node.left, SpanQuery)
        assert isinstance(node.right, SpanQuery)

    def test_overlap_round_trip(self):
        """Round-trip: overlap filter preserves structure."""
        round_trip("<np/> overlap <vp/>")


class TestCaseInsensitive:
    """Keywords are case-insensitive per Bcql.g4's caseInsensitive option."""

    def test_within_uppercase(self):
        """``"however" WITHIN <s/>`` shows that filter keywords are case-insensitive."""
        node = parse('"however" WITHIN <s/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"

    def test_containing_mixed_case(self):
        """``<s/> Containing "however"`` - mixed-case keyword is accepted and normalised."""
        node = parse('<s/> Containing "however"')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "containing"

    def test_case_insensitive_round_trips(self):
        """Round-trip normalises to lowercase."""
        round_trip('"however" WITHIN <s/>', expected='"however" within <s/>')
        round_trip('<s/> Containing "however"', expected='<s/> containing "however"')


class TestRightAssociativity:
    """Position filters are right-recursive: ``A within B within C`` -> ``A within (B within C)``."""

    def test_chained_within(self):
        """``"however" within <quote/> within <s/>`` demonstrates right-recursive filter chaining.

        The parser builds ``"however" within (<quote/> within <s/>)`` rather than chaining from the
        left. That is a grammar detail worth making explicit because readers often expect a flat
        left-associative chain.
        """
        node = parse('"however" within <quote/> within <s/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, TokenQuery)
        # Right side is another PositionFilterNode, not the left side
        assert isinstance(node.right, PositionFilterNode)
        assert node.right.operator == "within"
        assert isinstance(node.right.left, SpanQuery)
        assert node.right.left.tag_name == "quote"
        assert isinstance(node.right.right, SpanQuery)
        assert node.right.right.tag_name == "s"

    def test_chained_mixed_operators(self):
        """``"however" within <quote/> containing "said"`` mixes two right-recursive filter operators.

        The parser reads this as ``"however" within (<quote/> containing "said")``.
        """
        node = parse('"however" within <quote/> containing "said"')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.right, PositionFilterNode)
        assert node.right.operator == "containing"

    def test_chained_round_trip(self):
        """Round-trip: chained position filters preserve right-recursive structure."""
        round_trip('"however" within <quote/> within <s/>')
        round_trip('"however" within <quote/> containing "said"')


class TestWithGroups:
    """Position filters interact with groups and boolean operators."""

    def test_grouped_filter(self):
        """``("the" "committee") within <np/>`` uses a grouped sequence as the left operand."""
        node = parse('("the" "committee") within <np/>')
        assert isinstance(node, PositionFilterNode)
        assert isinstance(node.left, GroupNode)

    def test_union_then_within(self):
        """``"however" | "therefore" within <s/>`` - union binds tighter than ``within``.

        The parser groups the lexical alternative first and only then applies the position filter.
        """
        node = parse('"however" | "therefore" within <s/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "|"

    def test_filter_in_group(self):
        """``("however" within <quote/>) "occurred"`` keeps the filter local to the grouped left branch.

        Without the parentheses, the parser would keep extending the filter's right-hand side.
        """
        node = parse('("however" within <quote/>) "occurred"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], GroupNode)
        inner = node.children[0].child
        assert isinstance(inner, PositionFilterNode)

    def test_grouped_round_trips(self):
        """Round-trip: grouped position filters preserve structure."""
        round_trip('("the" "committee") within <np/>')
        round_trip('("however" within <quote/>) "occurred"')
