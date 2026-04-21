"""Tests for XML span (tag) queries: ``<tag/>``, ``<tag>``, ``</tag>``.

Per ``Bcql.g4``'s ``tag`` rule, spans come in three forms:
- Whole span: ``<s/>`` - matches the entire span
- Start tag: ``<s>`` - matches the start position
- End tag: ``</s>`` - matches the end position

Tag names can be identifiers or quoted strings (for regex patterns).
Attributes follow the pattern ``name="value"``.
"""

from conftest import round_trip_test

from bcql_py.models.sequence import RepetitionNode, SequenceNode
from bcql_py.models.span import SpanQuery
from bcql_py.models.token import StringValue, TokenQuery
from bcql_py.parser import parse


class TestWholeSpan:
    """``<tag/>`` matches the entire span."""

    def test_simple_whole_span(self):
        """``<s/>`` - match the entire extent of a sentence span."""
        node = parse("<s/>")
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "s"
        assert node.position == "whole"
        assert node.attributes == {}

    def test_whole_span_with_attribute(self):
        """``<ne type="PERS"/>`` - match a named-entity span of type PERSON.

        The ``ne`` tag represents a named-entity annotation layer, and the ``type="PERS"``
        attribute filters to only person entities (e.g. "John Smith", "Marie Curie").
        """
        node = parse('<ne type="PERS"/>')
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "ne"
        assert node.position == "whole"
        assert "type" in node.attributes
        assert node.attributes["type"].value == "PERS"

    def test_whole_span_multiple_attributes(self):
        """``<ne type="PERS" subtype="first"/>`` - NE span with two filter attributes.

        Filters named entities to person names (type) that are specifically first names (subtype).
        """
        node = parse('<ne type="PERS" subtype="first"/>')
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "ne"
        assert len(node.attributes) == 2
        assert node.attributes["type"].value == "PERS"
        assert node.attributes["subtype"].value == "first"

    def test_whole_span_regex_name(self):
        """``<"person|location"/>`` - span tag name as regex pattern.

        When the tag name is a quoted string, it is treated as a regex. This matches
        spans whose tag is either "person" or "location".
        """
        node = parse('<"person|location"/>')
        assert isinstance(node, SpanQuery)
        assert isinstance(node.tag_name, StringValue)
        assert node.tag_name.value == "person|location"
        assert node.position == "whole"

    def test_round_trip_whole_span(self):
        """Round-trip: simple whole span preserves structure."""
        round_trip_test("<s/>")

    def test_round_trip_with_attribute(self):
        """Round-trip: span with attribute preserves structure."""
        round_trip_test('<ne type="PERS"/>')

    def test_round_trip_regex_name(self):
        """Round-trip: span with regex tag name preserves structure."""
        round_trip_test('<"person|location"/>')

    def test_round_trip_multiple_attrs(self):
        """Round-trip: span with multiple attributes preserves structure."""
        round_trip_test('<ne type="PERS" subtype="first"/>')


class TestStartTag:
    """``<tag>`` matches the start position of a span."""

    def test_simple_start_tag(self):
        """``<s>`` - match the position where a sentence starts."""
        node = parse("<s>")
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "s"
        assert node.position == "start"
        assert node.attributes == {}

    def test_start_tag_with_attribute(self):
        """``<ne type="PERS">`` - match where a PERSON named-entity span starts."""
        node = parse('<ne type="PERS">')
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "ne"
        assert node.position == "start"
        assert node.attributes["type"].value == "PERS"

    def test_round_trip_start_tag(self):
        """Round-trip: start tag preserves structure."""
        round_trip_test("<s>")


class TestEndTag:
    """``</tag>`` matches the end position of a span."""

    def test_simple_end_tag(self):
        """``</s>`` - match the position where a sentence ends."""
        node = parse("</s>")
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "s"
        assert node.position == "end"
        assert node.attributes == {}

    def test_round_trip_end_tag(self):
        """Round-trip: end tag preserves structure."""
        round_trip_test("</s>")


class TestSpanInSequence:
    """Spans embedded in sequences and with repetition."""

    def test_start_tag_then_token(self):
        """``<s> []`` - sentence start followed by any token: the first word of every sentence."""
        node = parse("<s> []")
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], SpanQuery)
        assert node.children[0].position == "start"
        assert isinstance(node.children[1], TokenQuery)

    def test_token_then_end_tag(self):
        """``"that" </s>`` - sentences that end with the word "that"."""
        node = parse('"that" </s>')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], TokenQuery)
        assert isinstance(node.children[1], SpanQuery)
        assert node.children[1].position == "end"

    def test_span_with_repetition(self):
        """``<s/>+`` - repetition applied to a span (unusual but syntactically valid)."""
        node = parse("<s/>+")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert isinstance(node.child, SpanQuery)

    def test_round_trip_start_tag_sequence(self):
        """Round-trip: start tag in sequence preserves structure."""
        round_trip_test("<s> []")

    def test_round_trip_token_end_tag(self):
        """Round-trip: token before end tag preserves structure."""
        round_trip_test('"that" </s>')

    def test_round_trip_span_repetition(self):
        """Round-trip: span with repetition preserves structure."""
        round_trip_test("<s/>+")
