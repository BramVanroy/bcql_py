"""Tests for parsing token-level queries: ``[...]``, bare strings, ``_``, and the bracketed
constraint grammar (``&``, ``|``, ``!``, functions, integer ranges, parenthesised sub-expressions).
"""

from conftest import parse, round_trip

from bcql_py.models.sequence import UnderscoreNode
from bcql_py.models.token import (
    AnnotationConstraint,
    BoolConstraint,
    FunctionConstraint,
    IntegerRangeConstraint,
    NotConstraint,
    TokenQuery,
)


class TestTokenQueryEmpty:
    """``[]`` is the match-all pattern at token level."""

    def test_empty_brackets(self):
        """``[]`` matches any token regardless of its annotations."""
        node = parse("[]")
        assert isinstance(node, TokenQuery)
        assert node.constraint is None
        assert node.shorthand is None
        assert node.negated is False

    def test_empty_brackets_round_trip(self):
        """``[]`` survives parse -> to_bcql -> parse unchanged."""
        round_trip("[]")


class TestBareStringShorthand:
    """Bare strings are shorthand for ``[word=...]`` queries."""

    def test_double_quoted(self):
        """``"corpus"`` is shorthand for a word-form query on ``corpus``."""
        node = parse('"corpus"')
        assert isinstance(node, TokenQuery)
        assert node.shorthand is not None
        assert node.shorthand.value == "corpus"
        assert node.shorthand.is_literal is False

    def test_single_quoted(self):
        """``'corpus'`` shows that single and double quotes are interchangeable for regex strings."""
        node = parse("'corpus'")
        assert isinstance(node, TokenQuery)
        assert node.shorthand is not None
        assert node.shorthand.value == "corpus"

    def test_literal_string(self):
        """``l"e.g."`` stores a literal string, so the period is not treated as regex syntax."""
        node = parse('l"e.g."')
        assert isinstance(node, TokenQuery)
        assert node.shorthand is not None
        assert node.shorthand.is_literal is True
        assert node.shorthand.value == "e.g."

    def test_regex_pattern(self):
        """``"(run|walk)(s|ing)?"`` demonstrates regex alternation and optional suffixes."""
        node = parse('"(run|walk)(s|ing)?"')
        assert isinstance(node, TokenQuery)
        assert node.shorthand.value == "(run|walk)(s|ing)?"

    def test_case_sensitive_flag(self):
        """``"(?-i)Panama"`` keeps the case-sensitivity flag inside the stored string value."""
        node = parse('"(?-i)Panama"')
        assert isinstance(node, TokenQuery)
        assert node.shorthand.value == "(?-i)Panama"

    def test_round_trip_double_quoted(self):
        """``"corpus"`` round-trips unchanged."""
        round_trip('"corpus"')

    def test_round_trip_literal(self):
        """``l"e.g."`` round-trips unchanged."""
        round_trip('l"e.g."')


class TestUnderscore:
    """``_`` is the relation-query wildcard for one token position."""

    def test_underscore(self):
        """``_`` acts as a wildcard placeholder in relation and alignment queries."""
        node = parse("_")
        assert isinstance(node, UnderscoreNode)

    def test_underscore_round_trip(self):
        """``_`` round-trips unchanged."""
        round_trip("_")


class TestAnnotationConstraint:
    """Simple annotation comparisons such as ``[word=...]`` and ``[pos!=...]``."""

    def test_word_equals(self):
        """``[word="corpus"]`` explicitly queries the word-form annotation."""
        node = parse('[word="corpus"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.annotation == "word"
        assert c.operator == "="
        assert c.value.value == "corpus"
        assert c.value.is_literal is False

    def test_pos_not_equals(self):
        """``[pos != "noun"]`` excludes noun tags on the current token."""
        node = parse('[pos != "noun"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.annotation == "pos"
        assert c.operator == "!="

    def test_lemma_with_regex(self):
        """``[lemma="under.*"]`` queries lemmas that begin with ``under`` via regex."""
        node = parse('[lemma="under.*"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.value.value == "under.*"

    def test_literal_string_value(self):
        """``[lemma=l'etc.']`` uses a literal lemma string instead of a regex."""
        node = parse("[lemma=l'etc.']")
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.value.is_literal is True
        assert c.value.value == "etc."

    def test_round_trip_equals(self):
        """``[word="corpus"]`` round-trips unchanged."""
        round_trip('[word="corpus"]')

    def test_round_trip_not_equals(self):
        """``[pos!="noun"]`` normalises spacing around ``!=`` during round-trip."""
        round_trip('[pos!="noun"]')


class TestAnnotationComparisonOperators:
    """Extended comparison operators: ``<``, ``<=``, ``>``, and ``>=``."""

    def test_less_than(self):
        """``[pos_confidence<"50"]`` queries tokens with a confidence score below 50."""
        node = parse('[pos_confidence<"50"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.operator == "<"
        assert c.value.value == "50"

    def test_less_than_or_equal(self):
        """``[pos_confidence<="50"]`` allows scores up to and including 50."""
        node = parse('[pos_confidence<="50"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.operator == "<="

    def test_greater_than(self):
        """``[pos_confidence>"50"]`` keeps only scores above 50."""
        node = parse('[pos_confidence>"50"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.operator == ">"

    def test_greater_than_or_equal(self):
        """``[pos_confidence>="50"]`` keeps scores at least 50."""
        node = parse('[pos_confidence>="50"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, AnnotationConstraint)
        assert c.operator == ">="

    def test_round_trip_lt(self):
        """Round-trip: ``<`` comparison preserves structure."""
        round_trip('[pos_confidence<"50"]')

    def test_round_trip_lte(self):
        """Round-trip: ``<=`` comparison preserves structure."""
        round_trip('[pos_confidence<="50"]')

    def test_round_trip_gt(self):
        """Round-trip: ``>`` comparison preserves structure."""
        round_trip('[pos_confidence>"50"]')

    def test_round_trip_gte(self):
        """Round-trip: ``>=`` comparison preserves structure."""
        round_trip('[pos_confidence>="50"]')


class TestBoolConstraint:
    """Boolean operators inside token brackets.

    Like sequence-level boolean operators, ``&``, ``|``, and ``->`` all share the same precedence
    and are left-associative. That is a parser detail worth making explicit because many readers
    would expect ``&`` to bind tighter than ``|``.
    """

    def test_and(self):
        """``[lemma="search" & pos="noun"]`` keeps both constraints on the same token."""
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
        """``[word="however" | word="therefore"]`` matches either discourse connective."""
        node = parse('[word="however" | word="therefore"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "|"
        assert isinstance(c.left, AnnotationConstraint)
        assert c.left.annotation == "word"
        assert c.left.value.value == "however"
        assert isinstance(c.right, AnnotationConstraint)
        assert c.right.annotation == "word"
        assert c.right.value.value == "therefore"

    def test_left_associativity(self):
        """``[lemma="be" & pos="V" | word="is"]`` groups as ``(lemma="be" & pos="V") | word="is"``."""
        node = parse('[lemma="be" & pos="V" | word="is"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "|"
        assert isinstance(c.left, BoolConstraint)
        assert c.left.operator == "&"
        assert isinstance(c.right, AnnotationConstraint)

    def test_round_trip_embedded(self):
        """Round-trip: mixed boolean constraint preserves left-associative structure."""
        round_trip('[lemma="be" & pos="V" | word="is"]')

    def test_round_trip_and(self):
        """Round-trip: conjunction inside brackets preserves structure."""
        round_trip('[lemma="search" & pos="noun"]')

    def test_round_trip_chained(self):
        """Round-trip: chained boolean constraint preserves structure."""
        round_trip('[lemma="be" & pos="V" | word="is"]')

    def test_implication(self):
        """``[word="not" -> pos="ADV"]`` encodes a realistic token-level implication."""
        node = parse('[word="not" -> pos="ADV"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "->"
        assert isinstance(c.left, AnnotationConstraint)
        assert isinstance(c.right, AnnotationConstraint)
        assert c.left.value.value == "not"
        assert c.right.value.value == "ADV"

    def test_implication_left_associativity(self):
        """``[word="not" -> pos="ADV" & lemma="not"]`` groups left-to-right at one precedence level."""
        node = parse('[word="not" -> pos="ADV" & lemma="not"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "&"
        assert isinstance(c.left, BoolConstraint)
        assert c.left.operator == "->"
        assert isinstance(c.right, AnnotationConstraint)

    def test_round_trip_implication(self):
        """Round-trip: implication inside brackets preserves structure."""
        round_trip('[word="not" -> pos="ADV"]')

    def test_round_trip_mixed_implication(self):
        """Round-trip: implication plus conjunction preserves left-associative structure."""
        round_trip('[word="not" -> pos="ADV" & lemma="not"]')


class TestNotConstraint:
    """Negation inside token brackets: ``[!expr]``."""

    def test_simple_negation(self):
        """``[!pos="noun"]`` excludes noun tags at the current token position."""
        node = parse('[!pos="noun"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, NotConstraint)
        assert isinstance(c.operand, AnnotationConstraint)
        assert c.operand.annotation == "pos"

    def test_negation_of_parenthesised(self):
        """``[!(pos="noun" | pos="verb")]`` negates a grouped disjunction."""
        node = parse('[!(pos="noun" | pos="verb")]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, NotConstraint)
        assert isinstance(c.operand, BoolConstraint)

    def test_round_trip_negation(self):
        """Round-trip: negated bracket constraint preserves structure."""
        round_trip('[!pos="noun"]')


class TestIntegerRangeConstraint:
    """Integer range syntax: ``[annotation=in[min,max]]``."""

    def test_basic_range(self):
        """``[pos_confidence=in[50,100]]`` constrains a numeric annotation to a closed interval."""
        node = parse("[pos_confidence=in[50,100]]")
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, IntegerRangeConstraint)
        assert c.annotation == "pos_confidence"
        assert c.min_val == 50
        assert c.max_val == 100

    def test_round_trip(self):
        """Round-trip: integer-range constraint preserves structure."""
        round_trip("[pos_confidence=in[50,100]]")


class TestFunctionConstraint:
    """Functions and pseudo-annotations inside token brackets."""

    def test_single_arg(self):
        """``[punctAfter(",")]`` targets tokens followed by a comma via a pseudo-annotation."""
        node = parse('[punctAfter(",")]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, FunctionConstraint)
        assert c.name == "punctAfter"
        assert len(c.args) == 1
        assert c.args[0].value == ","

    def test_multiple_args(self):
        """``[word("however", "therefore")]`` expresses two lexical alternatives as function args."""
        node = parse('[word("however", "therefore")]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, FunctionConstraint)
        assert c.name == "word"
        assert len(c.args) == 2
        assert c.args[0].value == "however"
        assert c.args[1].value == "therefore"

    def test_empty_args(self):
        """``[queryfunc()]`` shows that empty-argument function calls are accepted syntactically."""
        node = parse("[queryfunc()]")
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, FunctionConstraint)
        assert c.name == "queryfunc"
        assert c.args == []

    def test_round_trip(self):
        """Round-trip: pseudo-annotation function constraint preserves structure."""
        round_trip('[punctAfter(",")]')

    def test_round_trip_multiple_args(self):
        """Round-trip: multi-argument function constraint preserves structure."""
        round_trip('[word("however", "therefore")]')


class TestParenthesisedConstraint:
    """Parenthesised sub-expressions inside token brackets."""

    def test_parens_do_not_change_semantics(self):
        """``[(word="corpus")]`` is a redundant but valid parenthesised token constraint."""
        node = parse('[(word="corpus")]')
        assert isinstance(node, TokenQuery)
        assert isinstance(node.constraint, AnnotationConstraint)

    def test_parens_group_or(self):
        """``[(word="however" | word="therefore") & pos="ADV"]`` makes the grouping explicit.

        Parentheses are mostly documentary here because the parser already keeps ``&``, ``|``, and
        ``->`` at one precedence level, but the grouped structure should still be preserved.
        """
        node = parse('[(word="however" | word="therefore") & pos="ADV"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "&"
        assert isinstance(c.left, BoolConstraint)
        assert c.left.operator == "|"


class TestCombinedTokenConstraint:
    """Compound token constraints inspired by corpus-query guides."""

    def test_word_and_lemma_bigram_first_token(self):
        """``[word="mij"&lemma="ik"]`` constrains both surface form and lemma on one Dutch token."""
        node = parse('[word="mij"&lemma="ik"]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert c.operator == "&"

    def test_word_and_punct_after(self):
        """``[word="however" & punctAfter=","]`` models a common sentence-initial punctuation pattern."""
        node = parse('[word="however" & punctAfter=","]')
        assert isinstance(node, TokenQuery)
        c = node.constraint
        assert isinstance(c, BoolConstraint)
        assert isinstance(c.left, AnnotationConstraint)
        assert isinstance(c.right, AnnotationConstraint)
        assert c.right.annotation == "punctAfter"
