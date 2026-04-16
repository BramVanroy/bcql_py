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
        """``_ ==>nl _`` - find any token aligned with any token in the Dutch parallel field.

        In a parallel corpus (e.g. English-Dutch), the ``==>`` alignment operator queries
        cross-language correspondences. This finds all tokens that have a Dutch counterpart.
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

        The ``?`` after the field name makes the alignment optional. Tokens without a
        Dutch translation still match.
        """
        node = parse("_ ==>nl? _")
        assert isinstance(node, AlignmentNode)
        assert node.alignments[0].operator.optional is True
        assert node.alignments[0].operator.target_field == "nl"

    def test_typed(self):
        """``_ =word=>nl _`` - word-level alignment to Dutch field.

        The ``=word=>`` prefix filters by alignment type; here only word-level
        (as opposed to sentence-level) alignments are considered.
        """
        node = parse("_ =word=>nl _")
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
        that is aligned with the Dutch word "pluizig" (fluffy/fuzzy).
        """
        node = parse('"fluffy" ==>nl "pluizig"')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.source, TokenQuery)
        assert node.source.shorthand == StringValue(value="fluffy")
        assert isinstance(node.alignments[0].target, TokenQuery)

    def test_token_query_target(self):
        """``_ ==>nl [pos="N"]`` - any token aligned with a Dutch noun."""
        node = parse('_ ==>nl [pos="N"]')
        assert isinstance(node, AlignmentNode)
        assert isinstance(node.alignments[0].target, TokenQuery)


class TestAlignmentCaptureName:
    """Capture name override: ``name:==>field target``."""

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
    """Multiple alignment constraints separated by ``;``."""

    def test_two_targets(self):
        """``_ ==>nl _ ; ==>fr _`` - aligned with both Dutch and French parallel fields.

        Semicolons chain multiple alignment constraints. This finds tokens that have
        counterparts in both Dutch and French.
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
        from bcql_py.models.span import PositionFilterNode

        node = parse('(<s/>) containing "however" ==>nl _')
        assert isinstance(node, PositionFilterNode)
        assert isinstance(node.right, AlignmentNode)

    def test_captures_in_target(self):
        """``"and" w1:[] ==>nl "en" w2:[]`` - captures in alignment source and target.

        Capture labels on tokens inside the alignment allow global constraints to
        reference specific positions on both sides of the translation.
        """

        node = parse('"and" w1:[] ==>nl "en" w2:[]')
        assert isinstance(node, AlignmentNode)
        # Source is a sequence with a capture
        assert isinstance(node.source, SequenceNode)


class TestAlignmentRightRecursive:
    """Alignment targets can themselves contain relations or alignments."""

    def test_alignment_target_with_relation(self):
        """``_ ==>nl _ -obj-> _`` - alignment target contains a dependency relation.

        The Dutch-side target is itself a relation query: find tokens aligned with
        Dutch tokens that have an object dependent.
        """
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
            '(<s/>) containing "however" ==>nl _',
            "_ ==>nl _ -obj-> _",
        ],
    )
    def test_round_trip(self, query: str):
        round_trip(query)


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
