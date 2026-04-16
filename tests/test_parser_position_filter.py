"""Tests for position filter operators: within, containing, overlap."""

from conftest import parse, round_trip

from bcql_py.models.sequence import GroupNode, SequenceBoolNode, SequenceNode
from bcql_py.models.span import PositionFilterNode, SpanQuery
from bcql_py.models.token import TokenQuery


class TestWithin:
    """The ``within`` operator filters hits that occur inside a span."""

    def test_token_within_span(self):
        """``"baker" within <person/>``"""
        node = parse('"baker" within <person/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, SpanQuery)
        assert node.right.tag_name == "person"

    def test_sequence_within_span(self):
        """``"the" "cat" within <np/>``"""
        node = parse('"the" "cat" within <np/>')
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
        round_trip('"baker" within <person/>')

    def test_within_sequence_round_trip(self):
        round_trip('"the" "cat" within <np/>')


class TestContaining:
    """The ``containing`` operator filters spans that contain a hit."""

    def test_span_containing_token(self):
        """``<s/> containing "dog"``"""
        node = parse('<s/> containing "dog"')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "containing"
        assert isinstance(node.left, SpanQuery)
        assert isinstance(node.right, TokenQuery)

    def test_containing_round_trip(self):
        round_trip('<s/> containing "dog"')


class TestOverlap:
    """The ``overlap`` operator matches positions where two queries overlap."""

    def test_basic_overlap(self):
        """``<np/> overlap <vp/>``"""
        node = parse("<np/> overlap <vp/>")
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "overlap"
        assert isinstance(node.left, SpanQuery)
        assert isinstance(node.right, SpanQuery)

    def test_overlap_round_trip(self):
        round_trip("<np/> overlap <vp/>")


class TestCaseInsensitive:
    """Keywords are case-insensitive per Bcql.g4's caseInsensitive option."""

    def test_within_uppercase(self):
        node = parse('"a" WITHIN <s/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"

    def test_containing_mixed_case(self):
        node = parse('<s/> Containing "x"')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "containing"

    def test_case_insensitive_round_trips(self):
        """Round-trip normalises to lowercase."""
        round_trip('"a" WITHIN <s/>', expected='"a" within <s/>')
        round_trip('<s/> Containing "x"', expected='<s/> containing "x"')


class TestRightAssociativity:
    """Position filters are right-recursive: ``A within B within C`` -> ``A within (B within C)``."""

    def test_chained_within(self):
        """``"cat" within <np/> within <s/>``"""
        node = parse('"cat" within <np/> within <s/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, TokenQuery)
        # Right side is another PositionFilterNode, not the left side
        assert isinstance(node.right, PositionFilterNode)
        assert node.right.operator == "within"
        assert isinstance(node.right.left, SpanQuery)
        assert node.right.left.tag_name == "np"
        assert isinstance(node.right.right, SpanQuery)
        assert node.right.right.tag_name == "s"

    def test_chained_mixed_operators(self):
        """``"cat" within <np/> containing "dog"``"""
        node = parse('"cat" within <np/> containing "dog"')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.right, PositionFilterNode)
        assert node.right.operator == "containing"

    def test_chained_round_trip(self):
        round_trip('"cat" within <np/> within <s/>')
        round_trip('"cat" within <np/> containing "dog"')


class TestWithGroups:
    """Position filters interact with groups and boolean operators."""

    def test_grouped_filter(self):
        """``("the" "cat") within <np/>``"""
        node = parse('("the" "cat") within <np/>')
        assert isinstance(node, PositionFilterNode)
        assert isinstance(node.left, GroupNode)

    def test_union_then_within(self):
        """``"cat" | "dog" within <np/>`` - union binds tighter than within."""
        node = parse('"cat" | "dog" within <np/>')
        assert isinstance(node, PositionFilterNode)
        assert node.operator == "within"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "|"

    def test_filter_in_group(self):
        """``("cat" within <np/>) "sleeps"`` - filter inside a parenthesized group."""
        node = parse('("cat" within <np/>) "sleeps"')
        assert isinstance(node, SequenceNode)
        assert isinstance(node.children[0], GroupNode)
        inner = node.children[0].child
        assert isinstance(inner, PositionFilterNode)

    def test_grouped_round_trips(self):
        round_trip('("the" "cat") within <np/>')
        round_trip('("cat" within <np/>) "sleeps"')
