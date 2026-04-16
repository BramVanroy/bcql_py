"""Tests for XML span (tag) queries: ``<tag/>``, ``<tag>``, ``</tag>``.

Per ``Bcql.g4``'s ``tag`` rule, spans come in three forms:
- Whole span: ``<s/>`` - matches the entire span
- Start tag: ``<s>`` - matches the start position
- End tag: ``</s>`` - matches the end position

Tag names can be identifiers or quoted strings (for regex patterns).
Attributes follow the pattern ``name="value"``.
"""

from conftest import parse, round_trip

from bcql_py.models.sequence import RepetitionNode, SequenceNode
from bcql_py.models.span import SpanQuery
from bcql_py.models.token import StringValue, TokenQuery


class TestWholeSpan:
    """``<tag/>`` matches the entire span."""

    def test_simple_whole_span(self):
        node = parse("<s/>")
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "s"
        assert node.position == "whole"
        assert node.attributes == {}

    def test_whole_span_with_attribute(self):
        """``<ne type="PERS"/>``."""
        node = parse('<ne type="PERS"/>')
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "ne"
        assert node.position == "whole"
        assert "type" in node.attributes
        assert node.attributes["type"].value == "PERS"

    def test_whole_span_multiple_attributes(self):
        """``<ne type="PERS" subtype="first"/>``."""
        node = parse('<ne type="PERS" subtype="first"/>')
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "ne"
        assert len(node.attributes) == 2
        assert node.attributes["type"].value == "PERS"
        assert node.attributes["subtype"].value == "first"

    def test_whole_span_regex_name(self):
        """``<"person|location"/>``."""
        node = parse('<"person|location"/>')
        assert isinstance(node, SpanQuery)
        assert isinstance(node.tag_name, StringValue)
        assert node.tag_name.value == "person|location"
        assert node.position == "whole"

    def test_round_trip_whole_span(self):
        round_trip("<s/>")

    def test_round_trip_with_attribute(self):
        round_trip('<ne type="PERS"/>')

    def test_round_trip_regex_name(self):
        round_trip('<"person|location"/>')

    def test_round_trip_multiple_attrs(self):
        round_trip('<ne type="PERS" subtype="first"/>')


class TestStartTag:
    """``<tag>`` matches the start position of a span."""

    def test_simple_start_tag(self):
        node = parse("<s>")
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "s"
        assert node.position == "start"
        assert node.attributes == {}

    def test_start_tag_with_attribute(self):
        node = parse('<ne type="PERS">')
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "ne"
        assert node.position == "start"
        assert node.attributes["type"].value == "PERS"

    def test_round_trip_start_tag(self):
        round_trip("<s>")


class TestEndTag:
    """``</tag>`` matches the end position of a span."""

    def test_simple_end_tag(self):
        node = parse("</s>")
        assert isinstance(node, SpanQuery)
        assert node.tag_name == "s"
        assert node.position == "end"
        assert node.attributes == {}

    def test_round_trip_end_tag(self):
        round_trip("</s>")


class TestSpanInSequence:
    """Spans embedded in sequences and with repetition."""

    def test_start_tag_then_token(self):
        """``<s> []``: first word of each sentence."""
        node = parse("<s> []")
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], SpanQuery)
        assert node.children[0].position == "start"
        assert isinstance(node.children[1], TokenQuery)

    def test_token_then_end_tag(self):
        """``"that" </s>``: sentences ending with "that"."""
        node = parse('"that" </s>')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 2
        assert isinstance(node.children[0], TokenQuery)
        assert isinstance(node.children[1], SpanQuery)
        assert node.children[1].position == "end"

    def test_span_with_repetition(self):
        """``<s/>+``: repetition applies to the span."""
        node = parse("<s/>+")
        assert isinstance(node, RepetitionNode)
        assert node.min_count == 1
        assert isinstance(node.child, SpanQuery)

    def test_round_trip_start_tag_sequence(self):
        round_trip("<s> []")

    def test_round_trip_token_end_tag(self):
        round_trip('"that" </s>')

    def test_round_trip_span_repetition(self):
        round_trip("<s/>+")
