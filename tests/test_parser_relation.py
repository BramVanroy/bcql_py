"""Tests for relation parsing (Step 10): child relations, root relations, and semicolon chains."""

import pytest
from conftest import parse, round_trip

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.relation import RelationNode, RootRelationNode
from bcql_py.models.sequence import GroupNode, SequenceNode, UnderscoreNode
from bcql_py.models.token import StringValue, TokenQuery


class TestChildRelation:
    """Basic dependency child relation: source -type-> target."""

    def test_simple_typed(self):
        """``_ -obj-> _`` - find any head token that has a direct object ("obj") dependent.

        Searches for: dependency heads that have an ``obj`` child relation.
        Example intuition: in ``Researchers analyzed corpora``, ``analyzed`` can head an ``obj``
        relation to ``corpora``.
        """
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
        """``_ --> _`` - find any token with any dependency child, regardless of relation type."""
        node = parse("_ --> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].operator.relation_type is None

    def test_negated(self):
        """``_ !-obj-> _`` - negated relation: tokens that do NOT have an object dependent."""
        node = parse("_ !-obj-> _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.operator.negated is True
        assert child.operator.relation_type == "obj"

    def test_negated_untyped(self):
        """``_ !--> _`` - negated untyped relation: tokens with no dependency children at all."""
        node = parse("_ !--> _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.operator.negated is True
        assert child.operator.relation_type is None

    def test_target_field(self):
        """``_ -obj->corrected _`` - query the "corrected" annotation field for the object relation.

        Some corpora have multiple annotation fields (e.g. "original" vs "corrected").
        The ``->fieldname`` syntax after the arrow targets a specific field.
        """
        node = parse("_ -obj->corrected _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.operator.relation_type == "obj"
        assert child.operator.target_field == "corrected"

    def test_token_query_source_and_target(self):
        """``[pos="V"] -nsubj-> [pos="N"]`` - find a verb whose nominal subject is a noun.

        Constrains both the source (a verb) and target (a noun) of the "nsubj" relation.
        Searches for: verb-source tokens whose ``nsubj`` target is noun-tagged.
        """
        node = parse('[pos="V"] -nsubj-> [pos="N"]')
        assert isinstance(node, RelationNode)
        assert isinstance(node.source, TokenQuery)
        assert isinstance(node.children[0].target, TokenQuery)

    def test_string_shorthand_target(self):
        """``_ -obj-> "evidence"`` - find heads whose object dependent is the word ``evidence``.

        The target is a bare-string shorthand for ``[word="evidence"]``.
        """
        node = parse('_ -obj-> "evidence"')
        assert isinstance(node, RelationNode)
        target = node.children[0].target
        assert isinstance(target, TokenQuery)
        assert target.shorthand == StringValue(value="evidence")


class TestChildRelationLabel:
    """Capture labels on child relations: ``label:-type-> target``."""

    def test_labelled(self):
        """``_ A:-obj-> _`` - capture the object dependent under label A.

        The label is placed on the child relation itself, allowing global constraints to
        reference the dependent token.
        """
        node = parse("_ A:-obj-> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].label == "A"

    def test_labelled_negated(self):
        """``_ A:!-obj-> _`` - capture a negated object relation under label A."""
        node = parse("_ A:!-obj-> _")
        assert isinstance(node, RelationNode)
        child = node.children[0]
        assert child.label == "A"
        assert child.operator.negated is True

    def test_capture_label_on_source(self):
        """``B:_ -obj-> _`` - capture the head (source) token under label B.

        The label wraps the source at the capture level, not the relation operator.
        This allows global constraints to reference the head token's annotations.
        """
        node = parse("B:_ -obj-> _")
        assert isinstance(node, RelationNode)
        from bcql_py.models.capture import CaptureNode

        assert isinstance(node.source, CaptureNode)
        assert node.source.label == "B"
        assert isinstance(node.source.body, UnderscoreNode)


class TestSemicolonChain:
    """Multiple child constraints separated by ``;``."""

    def test_two_children(self):
        """``_ -nsubj-> _ ; -obj-> _`` - find a verb with both a subject and an object.

        Searches for: heads that satisfy both child-relation constraints simultaneously.
        Example intuition: a transitive verb with both ``nsubj`` and ``obj`` dependents.
        """
        node = parse("_ -nsubj-> _ ; -obj-> _")
        assert isinstance(node, RelationNode)
        assert len(node.children) == 2
        assert node.children[0].operator.relation_type == "nsubj"
        assert node.children[1].operator.relation_type == "obj"

    def test_three_children(self):
        """``_ -nsubj-> _ ; -obj-> _ ; -amod-> _`` - head with subject, object, and adjectival modifier."""
        node = parse("_ -nsubj-> _ ; -obj-> _ ; -amod-> _")
        assert isinstance(node, RelationNode)
        assert len(node.children) == 3

    def test_mixed_negated_and_positive(self):
        """``_ -nsubj-> _ ; !-obj-> "evidence"`` - has a subject, but its object is not ``evidence``."""
        node = parse('_ -nsubj-> _ ; !-obj-> "evidence"')
        assert isinstance(node, RelationNode)
        assert len(node.children) == 2
        assert node.children[0].operator.negated is False
        assert node.children[1].operator.negated is True

    def test_labelled_children(self):
        """``_ A:-nsubj-> _ ; B:-obj-> _`` - label subject as A, object as B.

        Labelling both children allows global constraints to compare their annotations:
        ``_ A:-nsubj-> _ ; B:-obj-> _ :: A.word = B.word`` (subject and object are the same word).
        """
        node = parse("_ A:-nsubj-> _ ; B:-obj-> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].label == "A"
        assert node.children[1].label == "B"


class TestRightRecursive:
    """Relations are right-recursive: ``_ -a-> _ -b-> _`` parses as ``_ -a-> (_ -b-> _)``."""

    def test_chained(self):
        """``_ -nsubj-> _ -amod-> _`` - the subject itself has an adjectival modifier.

        Searches for: heads whose subject node itself has an adjectival modifier.
        Parser detail: the target of the first relation is recursively parsed as another relation.
        """
        node = parse("_ -nsubj-> _ -amod-> _")
        assert isinstance(node, RelationNode)
        assert node.children[0].operator.relation_type == "nsubj"
        inner = node.children[0].target
        assert isinstance(inner, RelationNode)
        assert inner.children[0].operator.relation_type == "amod"

    def test_chained_three_deep(self):
        """``_ -a-> _ -b-> _ -c-> _`` - three levels of nested dependency.

        Each target is itself a relation with its own child. This allows querying
        chains of dependency relations in deeply nested syntactic structures.
        """
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
        """``^-obj-> _`` - match a dependency tree root with an object child.

        The ``^`` prefix marks this as a root relation: the source is the root node
        of the dependency tree rather than a specific token.
        """
        node = parse("^-obj-> _")
        assert isinstance(node, RootRelationNode)
        assert node.relation_type == "obj"
        assert isinstance(node.target, UnderscoreNode)
        assert node.label is None

    def test_untyped_root(self):
        """``^--> _`` - root of the dependency tree with any relation type to a child."""
        node = parse("^--> _")
        assert isinstance(node, RootRelationNode)
        assert node.relation_type is None

    def test_root_with_capture_label(self):
        """``A:^-obj-> _`` - capture label wraps the root relation.

        The label A is applied at the capture level, wrapping the entire root relation.
        """
        node = parse("A:^-obj-> _")
        from bcql_py.models.capture import CaptureNode

        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, RootRelationNode)

    def test_root_with_token_target(self):
        """``^-nsubj-> [pos="V"]`` - root's nominal subject must be a verb."""
        node = parse('^-nsubj-> [pos="V"]')
        assert isinstance(node, RootRelationNode)
        assert isinstance(node.target, TokenQuery)

    def test_root_target_with_child_relation(self):
        """``^--> _ -obj-> _`` - root's child itself has an object dependent.

        The root has any relation to a token that in turn has an "obj" child.
        """
        node = parse("^--> _ -obj-> _")
        assert isinstance(node, RootRelationNode)
        assert isinstance(node.target, RelationNode)


class TestRelationInContext:
    """Relations inside position filters, global constraints, groups, and sequences."""

    def test_relation_in_group(self):
        """``(_ -obj-> _)`` - parenthesized dependency query for embedding in larger expressions."""
        node = parse("(_ -obj-> _)")
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, RelationNode)

    def test_relation_in_sequence(self):
        """``"the" _ -obj-> _`` - "the" followed by a head with an object dependent.

        The sequence "the" + wildcard becomes the source of the relation. This finds
        patterns where "the" precedes a token that governs an object.
        """
        node = parse('"the" _ -obj-> _')
        assert isinstance(node, RelationNode)
        assert isinstance(node.source, SequenceNode)
        assert len(node.source.children) == 2

    def test_relation_with_global_constraint(self):
        """``_ -obj-> _ :: A.word = B.word`` - dependency query with a global capture constraint."""
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
            '_ -nsubj-> [pos="N"] ; -obj-> "evidence"',
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
        """``_ -obj`` without ``->`` should fail: incomplete relation operator."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ -obj")

    def test_semicolon_without_child(self):
        """``_ -obj-> _ ;`` - trailing semicolon with no following child should error."""
        with pytest.raises(BCQLSyntaxError):
            parse("_ -obj-> _ ;")

    def test_root_incomplete(self):
        """``^-`` without completing the arrow should fail."""
        with pytest.raises(BCQLSyntaxError):
            parse("^-")

    def test_bare_caret(self):
        """``^`` alone should error in the lexer."""
        with pytest.raises(BCQLSyntaxError):
            parse("^")
