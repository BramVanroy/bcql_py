"""Tests for relation parsing (Step 10): child relations, root relations, and semicolon chains."""

import pytest
from conftest import parse, round_trip

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.relation import RelationNode, RootRelationNode
from bcql_py.models.sequence import GroupNode, SequenceNode, UnderscoreNode
from bcql_py.models.token import StringValue, TokenQuery


class TestChildRelation:
    """Basic child relation: source -type-> target."""

    def test_simple_typed(self):
        node = parse("_ -obj-> _")
        assert isinstance(node, RelationNode)
        assert isinstance(node.source, UnderscoreNode)
        assert len(node.children) == 1
        child = node.children[0]
        assert child.operator.relation_type == "obj"
        assert child.operator.negated is False
        assert child.operator.target_field is None
        assert child.label is None
        assert isinstance(child.target, UnderscoreNode)

    def test_untyped(self):
        """``_ --> _`` has no relation type."""
        node = parse("_ --> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].operator.relation_type is None

    def test_negated(self):
        """``_ !-obj-> _`` is a negated relation."""
        node = parse("_ !-obj-> _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.operator.negated is True
        assert child.operator.relation_type == "obj"

    def test_negated_untyped(self):
        """``_ !--> _`` has negation but no type."""
        node = parse("_ !--> _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.operator.negated is True
        assert child.operator.relation_type is None

    def test_target_field(self):
        """``_ -obj->corrected _`` targets a different field."""
        node = parse("_ -obj->corrected _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.operator.relation_type == "obj"
        assert child.operator.target_field == "corrected"

    def test_token_query_source_and_target(self):
        """Relations with bracket token queries."""
        node = parse('[pos="V"] -nsubj-> [pos="N"]')
        assert isinstance(node, RelationNode)
        assert isinstance(node.source, TokenQuery)
        assert isinstance(node.children[0].target, TokenQuery)

    def test_string_shorthand_target(self):
        """Relations with bare string target."""
        node = parse('_ -obj-> "dog"')
        assert isinstance(node, RelationNode)
        target = node.children[0].target
        assert isinstance(target, TokenQuery)
        assert target.shorthand == StringValue(value="dog")


class TestChildRelationLabel:
    """Capture labels on child relations: ``label:-type-> target``."""

    def test_labelled(self):
        node = parse("_ A:-obj-> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].label == "A"

    def test_labelled_negated(self):
        node = parse("_ A:!-obj-> _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.label == "A"
        assert child.operator.negated is True

    def test_capture_label_on_source(self):
        """``B:_ -obj-> _`` - the label wraps the source at the capture level (inside the relation)."""
        node = parse("B:_ -obj-> _")
        assert isinstance(node, RelationNode)
        from bcql_py.models.capture import CaptureNode

        assert isinstance(node.source, CaptureNode)
        assert node.source.label == "B"
        assert isinstance(node.source.body, UnderscoreNode)


class TestSemicolonChain:
    """Multiple child constraints separated by ``;``."""

    def test_two_children(self):
        node = parse("_ -nsubj-> _ ; -obj-> _")
        assert isinstance(node, RelationNode)
        assert len(node.children) == 2
        assert node.children[0].operator.relation_type == "nsubj"
        assert node.children[1].operator.relation_type == "obj"

    def test_three_children(self):
        node = parse("_ -nsubj-> _ ; -obj-> _ ; -amod-> _")
        assert isinstance(node, RelationNode)
        assert len(node.children) == 3

    def test_mixed_negated_and_positive(self):
        """``_ -nsubj-> _ ; !-obj-> "dog"`` - mixed child constraints."""
        node = parse('_ -nsubj-> _ ; !-obj-> "dog"')
        assert isinstance(node, RelationNode)
        assert len(node.children) == 2
        assert node.children[0].operator.negated is False
        assert node.children[1].operator.negated is True

    def test_labelled_children(self):
        node = parse("_ A:-nsubj-> _ ; B:-obj-> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].label == "A"
        assert node.children[1].label == "B"


class TestRightRecursive:
    """Relations are right-recursive: ``_ -a-> _ -b-> _`` parses as ``_ -a-> (_ -b-> _)``."""

    def test_chained(self):
        node = parse("_ -nsubj-> _ -amod-> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].operator.relation_type == "nsubj"
        inner = node.children[0].target
        assert isinstance(inner, RelationNode)
        assert inner.children[0].operator.relation_type == "amod"

    def test_chained_three_deep(self):
        node = parse("_ -a-> _ -b-> _ -c-> _")
        assert isinstance(node, RelationNode)
        inner1 = node.children[0].target
        assert isinstance(inner1, RelationNode)
        inner2 = inner1.children[0].target
        assert isinstance(inner2, RelationNode)
        assert inner2.children[0].operator.relation_type == "c"


class TestRootRelation:
    """Root relations: ``^-type-> target``."""

    def test_typed_root(self):
        node = parse("^-obj-> _")
        assert isinstance(node, RootRelationNode)
        assert node.relation_type == "obj"
        assert isinstance(node.target, UnderscoreNode)
        assert node.label is None

    def test_untyped_root(self):
        node = parse("^--> _")
        assert isinstance(node, RootRelationNode)
        assert node.relation_type is None

    def test_root_with_capture_label(self):
        """``A:^-obj-> _`` - capture label handled by the capture level."""
        node = parse("A:^-obj-> _")
        from bcql_py.models.capture import CaptureNode

        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, RootRelationNode)

    def test_root_with_token_target(self):
        node = parse('^-nsubj-> [pos="V"]')
        assert isinstance(node, RootRelationNode)
        assert isinstance(node.target, TokenQuery)

    def test_root_target_with_child_relation(self):
        """``^--> _ -obj-> _`` - root target has its own child relation."""
        node = parse("^--> _ -obj-> _")
        assert isinstance(node, RootRelationNode)
        assert isinstance(node.target, RelationNode)


class TestRelationInContext:
    """Relations inside position filters, global constraints, groups, and sequences."""

    def test_relation_in_group(self):
        node = parse("(_ -obj-> _)")
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, RelationNode)

    def test_relation_in_sequence(self):
        """``"the" _ -obj-> _`` - the sequence is the source of the relation."""
        node = parse('"the" _ -obj-> _')
        assert isinstance(node, RelationNode)
        assert isinstance(node.source, SequenceNode)
        assert len(node.source.children) == 2

    def test_relation_with_global_constraint(self):
        node = parse("_ -obj-> _ :: A.word = B.word")
        from bcql_py.models.capture import GlobalConstraintNode

        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.body, RelationNode)


class TestRoundTrips:
    """Round-trip tests: parse -> to_bcql -> parse produces identical AST."""

    @pytest.mark.parametrize(
        "query",
        [
            "_ -obj-> _",
            "_ --> _",
            "_ !-obj-> _",
            "_ !--> _",
            "_ -obj->corrected _",
            "^-obj-> _",
            "^--> _",
            "_ -nsubj-> _ ; -obj-> _",
            "_ -nsubj-> _ ; !-obj-> _",
            '_ -nsubj-> [pos="N"] ; -obj-> "dog"',
            "_ -nsubj-> _ -amod-> _",
            "_ A:-obj-> _",
            "_ A:!-obj-> _",
            "_ A:-nsubj-> _ ; B:-obj-> _",
            "A:^-obj-> _",
            "^--> _ -obj-> _",
            "(_ -obj-> _) within (<s/>)",
        ],
    )
    def test_round_trip(self, query: str):
        round_trip(query)


class TestRelationErrors:
    """Error cases for relation parsing."""

    def test_incomplete_arrow(self):
        """``_ -obj`` without ``->`` should fail."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ -obj")

    def test_semicolon_without_child(self):
        """``_ -obj-> _ ;`` with trailing semicolon should error at EOF."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ -obj-> _ ;")

    def test_root_incomplete(self):
        """``^-`` without completing the arrow."""
        with pytest.raises(BCQLSyntaxError):
            parse("^-")

    def test_bare_caret(self):
        """``^`` alone should error in the lexer."""
        with pytest.raises(BCQLSyntaxError):
            parse("^")
