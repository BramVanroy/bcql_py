"""Tests for alignment parsing (Step 11): alignment arrows, optional flag, capture names, semicolon chains."""

import pytest
from conftest import parse, round_trip

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.alignment import AlignmentNode
from bcql_py.models.sequence import SequenceNode, UnderscoreNode
from bcql_py.models.token import StringValue, TokenQuery


class TestBasicAlignment:
    """Basic alignment: source ==>field target."""

    def test_simple(self):
        node = parse("_ ==>nl _")
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.source, UnderscoreNode)
        assert len(node.alignments) == 1
        align = node.alignments[0]
        assert align.operator.target_field == "nl"
        assert align.operator.optional is False
        assert align.operator.relation_type is None
        assert align.operator.capture_name is None
        assert isinstance(align.target, UnderscoreNode)

    def test_optional(self):
        """``==>nl?`` marks the alignment as optional."""
        node = parse("_ ==>nl? _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.optional is True
        assert node.alignments[0].operator.target_field == "nl"

    def test_typed(self):
        """``=word=>nl`` filters by alignment type."""
        node = parse("_ =word=>nl _")
        assert isinstance(node, AlignmentNode)
        op = node.alignments[0].operator
        assert op.relation_type == "word"
        assert op.target_field == "nl"

    def test_typed_optional(self):
        node = parse("_ =word=>nl? _")
        assert isinstance(node, AlignmentNode)
        op = node.alignments[0].operator
        assert op.relation_type == "word"
        assert op.optional is True

    def test_string_source_and_target(self):
        node = parse('"fluffy" ==>nl "pluizig"')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.source, TokenQuery)
        assert node.source.shorthand == StringValue(value="fluffy")
        assert isinstance(node.alignments[0].target, TokenQuery)

    def test_token_query_target(self):
        node = parse('_ ==>nl [pos="N"]')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.alignments[0].target, TokenQuery)


class TestAlignmentCaptureName:
    """Capture name override: ``name:==>field target``."""

    def test_named(self):
        node = parse("_ alignments:==>nl _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.capture_name == "alignments"

    def test_named_typed(self):
        node = parse("_ myrels:=word=>nl _")
        assert isinstance(node, AlignmentNode)
        op = node.alignments[0].operator
        assert op.capture_name == "myrels"
        assert op.relation_type == "word"


class TestAlignmentSemicolonChain:
    """Multiple alignment constraints separated by ``;``."""

    def test_two_targets(self):
        node = parse("_ ==>nl _ ; ==>fr _")
        assert isinstance(node, AlignmentNode)
        assert len(node.alignments) == 2
        assert node.alignments[0].operator.target_field == "nl"
        assert node.alignments[1].operator.target_field == "fr"

    def test_three_targets(self):
        node = parse("_ ==>nl _ ; ==>fr _ ; ==>de _")
        assert isinstance(node, AlignmentNode)
        assert len(node.alignments) == 3

    def test_mixed_optional_and_required(self):
        node = parse("_ ==>nl _ ; ==>fr? _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.optional is False
        assert node.alignments[1].operator.optional is True

    def test_with_string_targets(self):
        node = parse('"fluffy" ==>nl "pluizig" ; ==>de "flauschig"')
        assert isinstance(node, AlignmentNode)
        assert len(node.alignments) == 2


class TestAlignmentInContext:
    """Alignments combined with other constructs."""

    def test_sequence_source(self):
        """``"and" [] ==>nl "en" []`` - source is a sequence."""
        node = parse('"and" [] ==>nl "en" []')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.source, SequenceNode)

    def test_alignment_in_position_filter(self):
        """Position filters wrap alignment queries."""
        from bcql_py.models.span import PositionFilterNode

        node = parse('(<s/>) containing "cat" ==>nl _')
        assert isinstance(node, PositionFilterNode)
        assert isinstance(node.right, AlignmentNode)

    def test_captures_in_target(self):
        """``w1:[] ==>nl w2:[]`` - captures inside alignment source and target."""

        node = parse('"and" w1:[] ==>nl "en" w2:[]')
        assert isinstance(node, AlignmentNode)
        # Source is a sequence with a capture
        assert isinstance(node.source, SequenceNode)


class TestAlignmentRightRecursive:
    """Alignment targets can themselves contain relations or alignments."""

    def test_alignment_target_with_relation(self):
        """The target of an alignment is a full rel_align."""
        node = parse("_ ==>nl _ -obj-> _")
        assert isinstance(node, AlignmentNode)
        from bcql_py.models.relation import RelationNode

        assert isinstance(node.alignments[0].target, RelationNode)


class TestRoundTrips:
    """Round-trip tests: parse -> to_bcql -> parse produces identical AST."""

    @pytest.mark.parametrize(
        "query",
        [
            "_ ==>nl _",
            "_ ==>nl? _",
            "_ =word=>nl _",
            "_ =word=>nl? _",
            "_ alignments:==>nl _",
            "_ myrels:=word=>nl _",
            "_ ==>nl _ ; ==>fr _",
            "_ ==>nl _ ; ==>fr _ ; ==>de _",
            "_ ==>nl _ ; ==>fr? _",
            '"fluffy" ==>nl "pluizig"',
            '"fluffy" ==>nl "pluizig" ; ==>de "flauschig"',
            '"and" w1:[] ==>nl "en" w2:[]',
            '(<s/>) containing "cat" ==>nl _',
            "_ ==>nl _ -obj-> _",
        ],
    )
    def test_round_trip(self, query: str):
        round_trip(query)


class TestAlignmentErrors:
    """Error cases for alignment parsing."""

    def test_missing_target_field(self):
        """``_ ==> _`` without a target field should fail."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ ==> _")

    def test_semicolon_without_child(self):
        """``_ ==>nl _ ;`` with trailing semicolon should error."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ ==>nl _ ;")
