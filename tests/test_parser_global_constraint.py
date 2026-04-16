"""Tests for global constraints (::) and the capture constraint grammar."""

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
        """``A:[] "by" B:[] :: A.word = B.word``"""
        node = parse('A:[] "by" B:[] :: A.word = B.word')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.body, SequenceNode)
        assert isinstance(node.constraint, ConstraintComparison)
        assert node.constraint.operator == "="

    def test_constraint_with_literal(self):
        """``A:[] :: A.word = "over"``"""
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
        """``A:[] B:[] :: A.word = "x" :: B.word = "y"`` - multiple :: are left-associative."""
        node = parse('A:[] B:[] :: A.word = "x" :: B.word = "y"')
        assert isinstance(node, GlobalConstraintNode)
        # Outer :: wraps everything
        assert isinstance(node.constraint, ConstraintComparison)
        assert node.constraint.left.label == "B"
        # Inner :: is the body
        assert isinstance(node.body, GlobalConstraintNode)
        assert isinstance(node.body.constraint, ConstraintComparison)
        assert node.body.constraint.left.label == "A"

    def test_round_trip(self):
        round_trip('A:[] "by" B:[] :: A.word = B.word')
        round_trip('A:[] :: A.word = "over"')

    def test_chained_round_trip(self):
        round_trip('A:[] B:[] :: A.word = "x" :: B.word = "y"')


class TestAnnotationRef:
    """``IDENT.IDENT`` annotation references in capture constraints."""

    def test_annotation_ref(self):
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
        round_trip("A:[] :: A.lemma = B.lemma")


class TestConstraintComparison:
    """Comparison operators in capture constraints."""

    @pytest.mark.parametrize("op", ["=", "!=", "<", "<=", ">", ">="])
    def test_all_comparison_operators(self, op):
        query = f'A:[] :: A.word {op} "cat"'
        node = parse(query)
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp, ConstraintComparison)
        assert cmp.operator == op

    @pytest.mark.parametrize("op", ["=", "!=", "<", "<=", ">", ">="])
    def test_comparison_round_trips(self, op):
        round_trip(f'A:[] :: A.word {op} "cat"')


class TestConstraintBoolean:
    """Boolean combination of capture constraints."""

    def test_and(self):
        node = parse('A:[] B:[] :: A.word = "x" & B.word = "y"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintBoolean)
        assert node.constraint.operator == "&"

    def test_or(self):
        node = parse('A:[] :: A.word = "x" | A.word = "y"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintBoolean)
        assert node.constraint.operator == "|"

    def test_implication(self):
        """``->`` implication in capture constraints - its primary use case."""
        node = parse('A:[] B:[] :: A.word = "cat" -> B.word = "dog"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintBoolean)
        assert node.constraint.operator == "->"

    def test_left_associative(self):
        """``a & b | c`` parses as ``(a & b) | c`` - all same precedence, left-to-right."""
        node = parse('A:[] :: A.word = "a" & A.lemma = "b" | A.pos = "c"')
        assert isinstance(node, GlobalConstraintNode)
        outer = node.constraint
        assert isinstance(outer, ConstraintBoolean)
        assert outer.operator == "|"
        assert isinstance(outer.left, ConstraintBoolean)
        assert outer.left.operator == "&"

    def test_boolean_round_trips(self):
        round_trip('A:[] B:[] :: A.word = "x" & B.word = "y"')
        round_trip('A:[] :: A.word = "x" | A.word = "y"')
        round_trip('A:[] B:[] :: A.word = "cat" -> B.word = "dog"')


class TestConstraintNot:
    """Negation in capture constraints."""

    def test_not(self):
        node = parse('A:[] :: !A.word = "bad"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintNot)
        inner = node.constraint.operand
        assert isinstance(inner, ConstraintComparison)

    def test_double_not(self):
        node = parse('A:[] :: !!A.word = "x"')
        assert isinstance(node, GlobalConstraintNode)
        assert isinstance(node.constraint, ConstraintNot)
        assert isinstance(node.constraint.operand, ConstraintNot)

    def test_not_round_trip(self):
        round_trip('A:[] :: !A.word = "bad"')


class TestConstraintFunctionCall:
    """Function calls in capture constraints like ``start(A)``."""

    def test_start_function(self):
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
        node = parse("A:[] :: end(A) = end(A)")
        assert isinstance(node, GlobalConstraintNode)
        cmp = node.constraint
        assert isinstance(cmp.left, ConstraintFunctionCall)
        assert cmp.left.name == "end"

    def test_function_multiple_args(self):
        node = parse('A:[] :: func(A.word, "lit")')
        assert isinstance(node, GlobalConstraintNode)
        fn = node.constraint
        assert isinstance(fn, ConstraintFunctionCall)
        assert fn.name == "func"
        assert len(fn.args) == 2
        assert isinstance(fn.args[0], AnnotationRef)
        assert isinstance(fn.args[1], ConstraintLiteral)

    def test_function_round_trips(self):
        round_trip("A:[] B:[] :: start(B) < start(A)")
        round_trip('A:[] :: func(A.word, "lit")')


class TestConstraintParentheses:
    """Parenthesized sub-expressions in capture constraints."""

    def test_parens_override_precedence(self):
        """``(a | b) & c`` vs default ``a | b & c`` which is ``(a | b) & c``."""
        node = parse('A:[] :: (A.word = "a" | A.word = "b") & A.pos = "c"')
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
            'A:[] :: (A.word = "a" | A.word = "b") & A.pos = "c"',
            expected='A:[] :: A.word = "a" | A.word = "b" & A.pos = "c"',
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
        round_trip("A:[] :: start(A)")
