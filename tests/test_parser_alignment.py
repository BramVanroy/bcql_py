"""Tests for alignment parsing (Step 11): alignment arrows, optional flag, capture names, semicolon chains."""

import pytest
from conftest import parse, round_trip_test

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.alignment import AlignmentNode
from bcql_py.models.capture import CaptureNode
from bcql_py.models.sequence import SequenceNode, UnderscoreNode
from bcql_py.models.span import PositionFilterNode
from bcql_py.models.token import StringValue, TokenQuery


class TestBasicAlignment:
    """Basic alignment: source ==>field target."""

    def test_simple(self):
        """``_ ==>nl _`` - find any token aligned with any token in the Dutch parallel field.

        In a parallel corpus (e.g. English<>Dutch), the ``==>`` alignment operator queries
        cross-language correspondences. In the "parallel" documentation, it is said that the field
        "nl" can be quired if the corpus has a field "contents__nl".
        """
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
        """``_ ==>nl? _`` - optional alignment: match even if no Dutch counterpart exists.

        From the documentation:
        > For example, if you're searching for translations of cat to Dutch, with ==>nl you will
        > only see instances where cat is aligned to a Dutch word;
        > on the other hand, with ==>nl? you will see both English cat hits where the
        > translation to Dutch was found, and cat hits where it wasn't.
        """
        node = parse("_ ==>nl? _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.optional is True
        assert node.alignments[0].operator.target_field == "nl"

    def test_typed(self):
        """``_ =word=>nl _`` - word-level alignment to Dutch field.
        I *assume* that this means that both source and target constraints "fluffy" and "pluizig" will
        be "looked up" in the "word" attributes but I am not sure.
        NOTE: see questions.md for the related question
        """
        node = parse('"fluffy" =word=>nl "pluizig"')
        assert isinstance(node, AlignmentNode)
        op = node.alignments[0].operator
        assert op.relation_type == "word"
        assert op.target_field == "nl"

    def test_typed_optional(self):
        """``_ =word=>nl? _`` - optional word-level alignment to Dutch field."""
        node = parse("_ =word=>nl? _")
        assert isinstance(node, AlignmentNode)
        op = node.alignments[0].operator
        assert op.relation_type == "word"
        assert op.optional is True

    def test_string_source_and_target(self):
        """``"fluffy" ==>nl "pluizig"`` - English "fluffy" aligned with Dutch "pluizig".

        Finds exact translation pairs in a parallel corpus: the English word "fluffy"
        that is aligned with the Dutch word "pluizig".
        """
        node = parse('"fluffy" ==>nl "pluizig"')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.source, TokenQuery)
        assert node.source.shorthand == StringValue(value="fluffy")
        assert isinstance(node.alignments[0].target, TokenQuery)

    def test_token_query_target(self):
        """``_ ==>nl [pos="N"]`` - any token aligned with a Dutch noun"""
        node = parse('_ ==>nl [pos="N"]')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.alignments[0].target, TokenQuery)


class TestAlignmentCaptureName:
    def test_named(self):
        """``_ alignments:==>nl _`` - custom capture name for the alignment set.

        The ``name:`` prefix before ``==>`` assigns a capture name to the alignment, allowing
        global constraints to reference it.
        """
        node = parse("_ alignments:==>nl _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.capture_name == "alignments"

    def test_named_typed(self):
        """``_ myrels:=word=>nl _`` - named and typed word-level alignment to Dutch."""
        node = parse("_ myrels:=word=>nl _")
        assert isinstance(node, AlignmentNode)
        op = node.alignments[0].operator
        assert op.capture_name == "myrels"
        assert op.relation_type == "word"


class TestAlignmentSemicolonChain:
    """Multiple alignment constraints can be separated by ``;``, similar to relations"""

    def test_two_targets(self):
        """``_ ==>nl _ ; ==>fr _`` - aligned with both Dutch and French parallel fields.

        Semicolons chain multiple alignment constraints. This finds tokens that have
        counterparts in both Dutch and French.

        TODO: I believe that that means this is in fact an intersection: the same source token must be aligned
          with both a Dutch and a French token. If it were a union, then we would find tokens that are aligned with Dutch OR French. Verify?
        """
        node = parse("_ ==>nl _ ; ==>fr _")
        assert isinstance(node, AlignmentNode)
        assert len(node.alignments) == 2
        assert node.alignments[0].operator.target_field == "nl"
        assert node.alignments[1].operator.target_field == "fr"

    def test_three_targets(self):
        """``_ ==>nl _ ; ==>fr _ ; ==>de _`` - aligned with Dutch, French, and German."""
        node = parse("_ ==>nl _ ; ==>fr _ ; ==>de _")
        assert isinstance(node, AlignmentNode)
        assert len(node.alignments) == 3

    def test_mixed_optional_and_required(self):
        """``_ ==>nl _ ; ==>fr? _`` - Dutch alignment required, French alignment optional."""
        node = parse("_ ==>nl _ ; ==>fr? _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.optional is False
        assert node.alignments[1].operator.optional is True

    def test_with_string_targets(self):
        """``"fluffy" ==>nl "pluizig" ; ==>de "flauschig"`` - translation pairs in two languages.

        Finds English "fluffy" aligned with Dutch "pluizig" and German "flauschig".
        """
        node = parse('"fluffy" ==>nl "pluizig" ; ==>de "flauschig"')
        assert isinstance(node, AlignmentNode)
        assert len(node.alignments) == 2


class TestAlignmentInContext:
    """Alignments combined with other constructs."""

    def test_sequence_source(self):
        """``"and" [] ==>nl "en" []`` - multi-word source aligned with multi-word Dutch target.

        Sequences on both sides of the alignment operator allow querying multi-word
        translation correspondences.
        """
        node = parse('"and" [] ==>nl "en" []')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.source, SequenceNode)

    def test_alignment_in_position_filter(self):
        """Position filters wrap alignment queries: ``containing "however" ==>nl _``."""
        node = parse('<s/> containing "however" ==>nl _')
        assert isinstance(node, PositionFilterNode)
        assert isinstance(node.right, AlignmentNode)

    def test_captures_in_target(self):
        """``"and" w1:[] ==>nl "en" w2:[]`` - captures in alignment source and target.

        Capture labels on tokens inside the alignment allow global constraints to
        reference specific positions on both sides of the translation.
        """

        node = parse('"and" w1:[] ==>nl "en" w2:[]')
        assert isinstance(node, AlignmentNode)

        assert isinstance(node.source, SequenceNode)
        assert len(node.source.children) == 2
        assert isinstance(node.source.children[0], TokenQuery)
        assert isinstance(node.source.children[1], CaptureNode)
        assert node.source.children[1].label == "w1"

        assert isinstance(node.alignments[0].target, SequenceNode)
        assert len(node.alignments[0].target.children) == 2
        assert isinstance(node.alignments[0].target.children[0], TokenQuery)
        assert isinstance(node.alignments[0].target.children[1], CaptureNode)
        assert node.alignments[0].target.children[1].label == "w2"


class TestAlignmentRightRecursive:
    """Alignment targets can themselves contain relations or alignments."""

    def test_alignment_target_with_relation(self):
        """``_ ==>nl _ -obj-> _`` - alignment target contains a dependency relation.

        The Dutch-side target is itself a relation query: find tokens aligned with
        Dutch tokens that have an object dependent.

        So with brackets that would read like ``_ ==>nl (_ -obj-> _)``.
        """
        node = parse("_ ==>nl _ -obj-> _")
        assert isinstance(node, AlignmentNode)
        from bcql_py.models.relation import RelationNode

        assert isinstance(node.alignments[0].target, RelationNode)


class TestAlignmentRoundTrips:
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
            '(<s/>) containing "however" ==>nl _',
            "_ ==>nl _ -obj-> _",
        ],
    )
    def test_round_trip(self, query: str):
        round_trip_test(query)


class TestAlignmentErrors:
    """Error cases for alignment parsing."""

    def test_missing_target_field(self):
        """``_ ==> _`` - missing target field after ``==>`` should fail."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ ==> _")

    def test_semicolon_without_child(self):
        """``_ ==>nl _ ;`` - trailing semicolon with no following alignment should error."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ ==>nl _ ;")
