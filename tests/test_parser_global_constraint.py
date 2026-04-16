"""Tests for global constraints ``::`` and the capture-constraint grammar.

One parser peculiarity to keep in view here is that ``&``, ``|``, and ``->`` share the same
precedence inside capture constraints too. Parentheses therefore tend to be documentary rather than
changing the grouping, unless they introduce a nested sub-expression that the AST keeps explicitly.
"""

import pytest
from conftest import parse, round_trip

from bcql_py.models.capture import (
    AnnotationRef,
    ConstraintBoolean,
    ConstraintComparison,
    ConstraintFunctionCall,
    ConstraintLiteral,
    ConstraintNot,
    GlobalConstraintNode,
)
from bcql_py.models.sequence import SequenceNode


class TestGlobalConstraint:
    """The ``::`` operator attaches a capture constraint to a query body."""

    def test_simple_constraint(self):
        """``A:[] "by" B:[] :: A.word = B.word`` - find "X by X" where both words are identical.

        Captures A and B surround the word "by". The global constraint ``A.word = B.word``
        requires the word form of both captured positions to be the same, e.g. "day by day".
        """
        node = parse('A:[] "by" B:[] :: A.word = B.word')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.body, SequenceNode)
        assert isinstance(node.constraint, ConstraintComparison)
        assert node.constraint.operator == "="

    def test_constraint_with_literal(self):
        """``A:[] :: A.word = "over"`` - find any token captured as A whose word form is "over".

        A trivial constraint that could also be written as ``[word="over"]``, but demonstrates
        the literal comparison syntax in global constraints.
        """
        node = parse('A:[] :: A.word = "over"')
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp, ConstraintComparison)
        assert isinstance(cmp.left, AnnotationRef)
        assert cmp.left.label == "A"
        assert cmp.left.annotation == "word"
        assert isinstance(cmp.right, ConstraintLiteral)
        assert cmp.right.value == "over"

    def test_chained_double_colon(self):
        """``left:[] right:[] :: left.word = "however" :: right.word = "therefore"`` chains ``::`` twice.

        ``::`` is left-associative: the first constraint attaches to the body, and the second wraps
        that whole constrained query.
        """
        node = parse('left:[] right:[] :: left.word = "however" :: right.word = "therefore"')
        assert isinstance(node, GlobalConstraintNode)
        # Outer :: wraps everything
        assert isinstance(node.constraint, ConstraintComparison)
        assert node.constraint.left.label == "right"
        # Inner :: is the body
        assert isinstance(node.body, GlobalConstraintNode)
        assert isinstance(node.body.constraint, ConstraintComparison)
        assert node.body.constraint.left.label == "left"

    def test_round_trip(self):
        """Round-trip: global constraints preserve structure."""
        round_trip('A:[] "by" B:[] :: A.word = B.word')
        round_trip('A:[] :: A.word = "over"')

    def test_chained_round_trip(self):
        """Round-trip: chained global constraints preserve left-associative structure."""
        round_trip('left:[] right:[] :: left.word = "however" :: right.word = "therefore"')


class TestAnnotationRef:
    """``IDENT.IDENT`` annotation references in capture constraints."""

    def test_annotation_ref(self):
        """``A:[] :: A.word = B.word`` - compare annotations of two captured tokens.

        The ``LABEL.annotation`` syntax references a specific annotation layer of a captured
        position. Here, both A and B's ``word`` annotations are compared for equality.
        """
        node = parse("A:[] :: A.word = B.word")
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp, ConstraintComparison)
        assert isinstance(cmp.left, AnnotationRef)
        assert cmp.left.label == "A"
        assert cmp.left.annotation == "word"
        assert isinstance(cmp.right, AnnotationRef)
        assert cmp.right.label == "B"
        assert cmp.right.annotation == "word"

    def test_annotation_ref_round_trip(self):
        """Round-trip: annotation reference comparison preserves structure."""
        round_trip("A:[] :: A.lemma = B.lemma")


class TestConstraintComparison:
    """Comparison operators in capture constraints."""

    @pytest.mark.parametrize("op", ["=", "!=", "<", "<=", ">", ">="])
    def test_all_comparison_operators(self, op):
        query = f'focus:[] :: focus.word {op} "however"'
        node = parse(query)
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp, ConstraintComparison)
        assert cmp.operator == op

    @pytest.mark.parametrize("op", ["=", "!=", "<", "<=", ">", ">="])
    def test_comparison_round_trips(self, op):
        round_trip(f'focus:[] :: focus.word {op} "however"')


class TestConstraintBoolean:
    """Boolean combination of capture constraints."""

    def test_and(self):
        """``:: left.word = "however" & right.word = "therefore"`` requires both comparisons to hold.

        This is the typical use of ``&`` in capture constraints: combine requirements on multiple
        captures from one matched pattern.
        """
        node = parse('left:[] right:[] :: left.word = "however" & right.word = "therefore"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintBoolean)
        assert node.constraint.operator == "&"

    def test_or(self):
        """``:: focus.word = "however" | focus.word = "therefore"`` allows either lexical value.

        This is a common pattern when a capture may realise one of several discourse markers.
        """
        node = parse('focus:[] :: focus.word = "however" | focus.word = "therefore"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintBoolean)
        assert node.constraint.operator == "|"

    def test_implication(self):
        """``:: cue.word = "if" -> verb.pos = "V"`` shows the idiomatic use of implication in constraints.

        Implication is usually more meaningful here than at sequence level because it can express a
        conditional dependency between two captures.
        """
        node = parse('cue:[] verb:[] :: cue.word = "if" -> verb.pos = "V"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintBoolean)
        assert node.constraint.operator == "->"

    def test_left_associative(self):
        """``focus.word = "however" & focus.lemma = "however" | focus.pos = "ADV"`` groups left-to-right.

        This mirrors the same-precedence behaviour used by sequence and token constraints.
        """
        node = parse('focus:[] :: focus.word = "however" & focus.lemma = "however" | focus.pos = "ADV"')
        assert isinstance(node, GlobalConstraintNode)
        outer = node.constraint
        assert isinstance(outer, ConstraintBoolean)
        assert outer.operator == "|"
        assert isinstance(outer.left, ConstraintBoolean)
        assert outer.left.operator == "&"

    def test_boolean_round_trips(self):
        """Round-trip: boolean capture constraints preserve structure."""
        round_trip('left:[] right:[] :: left.word = "however" & right.word = "therefore"')
        round_trip('focus:[] :: focus.word = "however" | focus.word = "therefore"')
        round_trip('cue:[] verb:[] :: cue.word = "if" -> verb.pos = "V"')


class TestConstraintNot:
    """Negation in capture constraints."""

    def test_not(self):
        """``:: !focus.word = "however"`` negates a capture comparison.

        This is mostly a structural parser test, but it models the common need to exclude a
        specific lexical item after capturing a token.
        """
        node = parse('focus:[] :: !focus.word = "however"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintNot)
        inner = node.constraint.operand
        assert isinstance(inner, ConstraintComparison)

    def test_double_not(self):
        """``focus:[] :: !!focus.word = "however"`` keeps nested negation nodes explicit."""
        node = parse('focus:[] :: !!focus.word = "however"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintNot)
        assert isinstance(node.constraint.operand, ConstraintNot)

    def test_not_round_trip(self):
        """Round-trip: negated capture constraint preserves structure."""
        round_trip('focus:[] :: !focus.word = "however"')


class TestConstraintFunctionCall:
    """Function calls in capture constraints like ``start(A)``."""

    def test_start_function(self):
        """``:: start(B) < start(A)`` - B starts before A in the document.

        The ``start()`` function returns a capture's starting position. This constraint
        ensures that the token captured as B appears before the token captured as A.
        """
        node = parse("A:[] B:[] :: start(B) < start(A)")
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp, ConstraintComparison)
        assert cmp.operator == "<"
        assert isinstance(cmp.left, ConstraintFunctionCall)
        assert cmp.left.name == "start"
        assert len(cmp.left.args) == 1
        assert isinstance(cmp.left.args[0], AnnotationRef)
        assert cmp.left.args[0].label == "B"

    def test_end_function(self):
        """``:: end(A) = end(A)`` - trivially compare A's end position with itself.

        The ``end()`` function returns a capture's end position. This trivial comparison
        is used to test function call parsing, not for real queries.
        """
        node = parse("A:[] :: end(A) = end(A)")
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp.left, ConstraintFunctionCall)
        assert cmp.left.name == "end"

    def test_function_multiple_args(self):
        """``focus:[] :: func(focus.word, "ADV")`` mixes an annotation reference and a literal arg."""
        node = parse('focus:[] :: func(focus.word, "ADV")')
        assert isinstance(node, GlobalConstraintNode)
        fn = node.constraint
        assert isinstance(fn, ConstraintFunctionCall)
        assert fn.name == "func"
        assert len(fn.args) == 2
        assert isinstance(fn.args[0], AnnotationRef)
        assert isinstance(fn.args[1], ConstraintLiteral)

    def test_function_round_trips(self):
        """Round-trip: function calls in capture constraints preserve structure."""
        round_trip("A:[] B:[] :: start(B) < start(A)")
        round_trip('focus:[] :: func(focus.word, "ADV")')


class TestConstraintParentheses:
    """Parenthesized sub-expressions in capture constraints."""

    def test_parens_override_precedence(self):
        """``(focus.word = "however" | focus.word = "therefore") & focus.pos = "ADV"`` keeps the OR grouped.

        Because all three boolean operators share precedence, the grouped and ungrouped forms are
        effectively equivalent after round-trip. The parser still needs to build the grouped AST
        correctly when the parentheses are present in the source.
        """
        node = parse('focus:[] :: (focus.word = "however" | focus.word = "therefore") & focus.pos = "ADV"')
        assert isinstance(node, GlobalConstraintNode)
        outer = node.constraint
        assert isinstance(outer, ConstraintBoolean)
        assert outer.operator == "&"
        # Left side is the parenthesized OR
        assert isinstance(outer.left, ConstraintBoolean)
        assert outer.left.operator == "|"

    def test_parens_round_trip(self):
        # Parens are structural only; since & | -> have same precedence, the flat form is equivalent
        round_trip(
            'focus:[] :: (focus.word = "however" | focus.word = "therefore") & focus.pos = "ADV"',
            expected='focus:[] :: focus.word = "however" | focus.word = "therefore" & focus.pos = "ADV"',
        )


class TestBareLabel:
    """Bare identifiers (capture labels) used as function arguments."""

    def test_bare_label_in_function(self):
        """``start(A)`` - A is a bare capture label."""
        node = parse("A:[] :: start(A)")
        fn = node.constraint
        assert isinstance(fn, ConstraintFunctionCall)
        assert isinstance(fn.args[0], AnnotationRef)
        assert fn.args[0].label == "A"
        assert fn.args[0].annotation == ""

    def test_bare_label_round_trips(self):
        """Round-trip: bare label in function argument preserves structure."""
        round_trip("A:[] :: start(A)")
