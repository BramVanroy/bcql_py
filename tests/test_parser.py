import pytest

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.sequence import UnderscoreNode
from bcql_py.models.token import (
    AnnotationConstraint,
    BoolConstraint,
    FunctionConstraint,
    IntegerRangeConstraint,
    NotConstraint,
    TokenQuery,
)

from conftest import parse, round_trip


class TestTokenQueryEmpty:
    """``[]``: the match-all pattern."""

    def test_empty_brackets(self):
        node = parse("[]")
        assert isinstance(node, TokenQuery)
        assert node.constraint is None
        assert node.shorthand is None
        assert node.negated is False

    def test_empty_brackets_round_trip(self):
        round_trip("[]")


class TestBareStringShorthand:
    """``"man"``: shorthand for ``[word="man"]``."""
    def test_double_quoted(self):
        node = parse('"man"')
        assert isinstance(node, TokenQuery)
        assert node.shorthand is not None
        assert node.shorthand.value == "man"
        assert node.shorthand.is_literal is False

    def test_single_quoted(self):
        node = parse("'man'")
        assert isinstance(node, TokenQuery)
        assert node.shorthand is not None
        assert node.shorthand.value == "man"

    def test_literal_string(self):
        node = parse('l"e.g."')
        assert isinstance(node, TokenQuery)
        assert node.shorthand is not None
        assert node.shorthand.is_literal is True
        assert node.shorthand.value == "e.g."

    def test_regex_pattern(self):
        node = parse('"(wo)?man"')
        assert isinstance(node, TokenQuery)
        assert node.shorthand.value == "(wo)?man"

    def test_case_sensitive_flag(self):
        """``"(?-i)Panama"``: sensitivity is stored as part of the string value"""
        node = parse('"(?-i)Panama"')
        assert isinstance(node, TokenQuery)
        assert node.shorthand.value == "(?-i)Panama"

    def test_round_trip_double_quoted(self):
        round_trip('"man"')

    def test_round_trip_literal(self):
        round_trip('l"e.g."')


class TestUnderscore:
    """``_``: the wildcard for relation queries."""
    def test_underscore(self):
        node = parse("_")
        assert isinstance(node, UnderscoreNode)

    def test_underscore_round_trip(self):
        round_trip("_")


class TestAnnotationConstraint:
    """``[annotation = "value"]`` and ``[annotation != "value"]``."""
    def test_word_equals(self):
        node = parse('[word="man"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.annotation == "word"
        assert c.operator == "="
        assert c.value.value == "man"
        assert c.value.is_literal is False

    def test_pos_not_equals(self):
        node = parse('[pos != "noun"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.annotation == "pos"
        assert c.operator == "!="

    def test_lemma_with_regex(self):
        node = parse('[lemma="under.*"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.value.value == "under.*"

    def test_literal_string_value(self):
        node = parse("[lemma=l'etc.']")
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.value.is_literal is True
        assert c.value.value == "etc."

    def test_round_trip_equals(self):
        round_trip('[word="man"]')

    def test_round_trip_not_equals(self):
        # Parser normalises away whitespace around !=
        round_trip('[pos!="noun"]')


class TestBoolConstraint:
    """``[a & b]``, ``[a | b]``, and chained combinations inside token brackets.
    Note that these are different from the boolean operators on the query level (AND, OR) and have different precedence rules.
    """

    def test_and(self):
        node = parse('[lemma="search" & pos="noun"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "&"
        assert isinstance(c.left, AnnotationConstraint)
        assert isinstance(c.right, AnnotationConstraint)
        assert c.left.annotation == "lemma"
        assert c.right.annotation == "pos"

    def test_or(self):
        node = parse('[word="man" | word="woman"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "|"

    def test_left_associativity(self):
        """``a & b | c`` should parse as ``(a & b) | c``: same precedence, left-to-right."""
        node = parse('[word="a" & word="b" | word="c"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "|"
        # Left operand is the (a & b)
        assert isinstance(c.left, BoolConstraint)
        assert c.left.operator == "&"
        # Right operand is c
        assert isinstance(c.right, AnnotationConstraint)

    def test_round_trip_and(self):
        round_trip('[lemma="search" & pos="noun"]')

    def test_round_trip_chained(self):
        round_trip('[word="a" & word="b" | word="c"]')


class TestNotConstraint:
    """``[!expr]``: negation inside token brackets."""

    def test_simple_negation(self):
        node = parse('[!pos="noun"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, NotConstraint)
        assert isinstance(c.operand, AnnotationConstraint)
        assert c.operand.annotation == "pos"

    def test_negation_of_parenthesised(self):
        node = parse('[!(pos="noun" | pos="verb")]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, NotConstraint)
        assert isinstance(c.operand, BoolConstraint)

    def test_round_trip_negation(self):
        round_trip('[!pos="noun"]')


class TestIntegerRangeConstraint:
    """``[annotation=in[min,max]]``."""

    def test_basic_range(self):
        node = parse("[pos_confidence=in[50,100]]")
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, IntegerRangeConstraint)
        assert c.annotation == "pos_confidence"
        assert c.min_val == 50
        assert c.max_val == 100

    def test_round_trip(self):
        round_trip("[pos_confidence=in[50,100]]")


class TestFunctionConstraint:
    """``[name(args)]``: function / pseudo-annotation inside brackets."""

    def test_single_arg(self):
        node = parse('[punctAfter(",")]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, FunctionConstraint)
        assert c.name == "punctAfter"
        assert len(c.args) == 1
        assert c.args[0].value == ","

    def test_multiple_args(self):
        node = parse('[word("man", "woman")]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, FunctionConstraint)
        assert c.name == "word"
        assert len(c.args) == 2
        assert c.args[0].value == "man"
        assert c.args[1].value == "woman"

    def test_empty_args(self):
        node = parse("[myFunc()]")
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, FunctionConstraint)
        assert c.name == "myFunc"
        assert c.args == []

    def test_round_trip(self):
        round_trip('[punctAfter(",")]')

    def test_round_trip_multiple_args(self):
        round_trip('[word("man", "woman")]')


class TestParenthesisedConstraint:
    """``[(expr)]``: parenthesised sub-expression inside brackets."""

    def test_parens_do_not_change_semantics(self):
        node = parse('[(word="man")]')
        assert isinstance(node, TokenQuery)
        # Parentheses are transparent: the inner expr is returned directly
        assert isinstance(node.constraint, AnnotationConstraint)

    def test_parens_group_or(self):
        """``(a | b) & c``: parens override left-to-right."""
        node = parse('[(word="a" | word="b") & pos="noun"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "&"
        # Left should be the OR
        assert isinstance(c.left, BoolConstraint)
        assert c.left.operator == "|"


class TestCombinedTokenConstraint:
    """Compound expressions from the example queries guide."""

    def test_word_and_lemma_bigram_first_token(self):
        """``[word="mij"&lemma="ik"]``: multiple annotations on one token."""
        node = parse('[word="mij"&lemma="ik"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "&"

    def test_word_and_punct_after(self):
        """``[word="dog" & punctAfter=","]``."""
        node = parse('[word="dog" & punctAfter=","]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert isinstance(c.left, AnnotationConstraint)
        assert isinstance(c.right, AnnotationConstraint)
        assert c.right.annotation == "punctAfter"


class TestParserErrors:
    """Syntax errors should include position information."""

    def test_unclosed_bracket(self):
        with pytest.raises(BCQLSyntaxError, match="after annotation name"):
            parse("[word")

    def test_missing_value(self):
        with pytest.raises(BCQLSyntaxError, match="string"):
            parse("[word=]")

    def test_empty_input(self):
        with pytest.raises(BCQLSyntaxError):
            parse("")

    def test_unknown_token_in_atom(self):
        with pytest.raises(BCQLSyntaxError):
            parse("&")

    def test_error_has_position(self):
        with pytest.raises(BCQLSyntaxError) as exc_info:
            parse("[word=]")
        assert exc_info.value.position is not None
