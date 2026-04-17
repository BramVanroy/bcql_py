"""Tests for parser error reporting: syntax errors with position information."""

import pytest
from conftest import round_trip_test

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.capture import AnnotationRef, GlobalConstraintNode
from bcql_py.models.token import NotConstraint, TokenQuery
from bcql_py.parser import BCQLParser, BCQLLexer, Token, TokenType, parse_from_tokens, parse


class TestParserErrors:
    """Syntax errors should include position information."""

    def test_unclosed_bracket(self):
        """``[word`` - missing closing bracket after annotation name."""
        with pytest.raises(BCQLSyntaxError, match="after annotation name"):
            parse("[word")

    def test_missing_value(self):
        """``[word=]`` - annotation comparison with no value after the operator."""
        with pytest.raises(BCQLSyntaxError, match="string"):
            parse("[word=]")

    def test_empty_input(self):
        """Empty string is not a valid query."""
        with pytest.raises(BCQLSyntaxError):
            parse("")

    def test_unknown_token_in_atom(self):
        """``&`` - operator cannot start a query; requires operands on both sides."""
        with pytest.raises(BCQLSyntaxError):
            parse("&")

    def test_error_has_position(self):
        """``[word=]`` - error should carry the character position of the failing token."""
        with pytest.raises(BCQLSyntaxError) as exc_info:
            parse("[word=]")
        assert exc_info.value.position is not None


class TestParserConstructorValidation:
    """BCQLParser constructor rejects invalid token lists."""

    def test_empty_token_list(self):
        """Parser rejects an empty token list (no input at all)."""
        with pytest.raises(BCQLSyntaxError, match="No tokens"):
            BCQLParser([], source="")

    def test_missing_eof(self):
        """Parser rejects a token list that is not terminated by an EOF sentinel."""
        tokens = [Token(TokenType.UNDERSCORE, "_", 0)]
        with pytest.raises(BCQLSyntaxError, match="end with EOF"):
            BCQLParser(tokens, source="_")

    def test_multiple_eof(self):
        """Parser rejects a token list with more than one EOF sentinel."""
        tokens = [
            Token(TokenType.UNDERSCORE, "_", 0),
            Token(TokenType.EOF, "", 1),
            Token(TokenType.EOF, "", 2),
        ]
        with pytest.raises(BCQLSyntaxError, match="exactly one EOF"):
            BCQLParser(tokens, source="_")


class TestTrailingTokens:
    """Trailing tokens after a valid query should raise an error."""

    def test_trailing_bracket(self):
        """``"however" ]`` - stray closing bracket after a complete query."""
        with pytest.raises(BCQLSyntaxError, match="Unexpected token"):
            parse('"however" ]')


class TestTagNameError:
    """Invalid tag name token raises an error."""

    def test_numeric_tag_name(self):
        """``<42/>`` - tag name must be an identifier or string, not a number."""
        with pytest.raises(BCQLSyntaxError, match="tag name"):
            parse("<42/>")


class TestTokenConstraintNonIdent:
    """Non-identifier where annotation name expected inside [...]."""

    def test_integer_inside_bracket(self):
        """``[42]`` - integer where an annotation name is expected inside brackets."""
        with pytest.raises(BCQLSyntaxError, match="annotation name"):
            parse("[42]")


class TestCaptureConstraintEdgeCases:
    """Edge cases in capture constraint parsing."""

    def test_bare_ident_in_cc(self):
        """``[word="however"] :: focus`` - bare capture label in a global constraint atom.

        Not semantically useful because ``focus`` is not bound, but it exercises the parser's bare-
        identifier path in capture-constraint atoms. A realistic query would be
        ``focus:[word="however"] :: start(focus) = 0``.
        """
        node = parse('[word="however"] :: focus')
        assert isinstance(node, GlobalConstraintNode)
        cc = node.constraint
        assert isinstance(cc, AnnotationRef)
        assert cc.label == "focus"
        assert cc.annotation == ""

    def test_invalid_token_in_cc(self):
        """``[word="however"] :: <`` - angle bracket is not valid at start of a capture constraint."""
        with pytest.raises(BCQLSyntaxError, match="capture constraint"):
            parse('[word="however"] :: <')


class TestNotConstraintParenWrap:
    """NotConstraint wraps BoolConstraint operand in parens during to_bcql."""

    def test_not_bool_constraint_round_trip(self):
        """``[!(word="however" & pos="ADV")]`` - negated grouped token constraint round-trips with parens.

        The NotConstraint wraps a BoolConstraint, requiring parens in the round-trip output
        to preserve the grouping.
        """
        round_trip_test('[!(word="however" & pos="ADV")]')

    def test_not_bool_constraint_structure(self):
        """``[!(word="however" & pos="ADV")]`` - grouped negation stays explicit in the AST."""
        node = parse('[!(word="however" & pos="ADV")]')
        assert isinstance(node, TokenQuery)
        assert isinstance(node.constraint, NotConstraint)


class TestErrorPosition:
    """BCQLSyntaxError.position points at the offending token with ``^``, not past it."""

    def test_unterminated_string_position(self):
        """``[lemma='etc]`` - caret should point at the opening quote, not end of input."""
        with pytest.raises(BCQLSyntaxError) as exc_info:
            parse("[lemma='etc]")
        # `'` is at index 7; must NOT be at end-of-string (len=12)
        assert exc_info.value.position == 7

    def test_unterminated_literal_string_position(self):
        """``[lemma=l'etc]`` - caret should point at the ``l`` prefix, not end of input."""
        with pytest.raises(BCQLSyntaxError) as exc_info:
            parse("[lemma=l'etc]")
        # `l` is at index 7; must NOT be at end-of-string (len=13)
        assert exc_info.value.position == 7

    def test_missing_value_position(self):
        """``[word=]`` - caret should point at the ``]``, not elsewhere."""
        with pytest.raises(BCQLSyntaxError) as exc_info:
            parse("[word=]")
        # `]` is at index 6
        assert exc_info.value.position == 6

    def test_error_position_not_past_end(self):
        """Error position must always be a valid index into the query string."""
        queries = ["[lemma='etc]", "[lemma=l'etc]", "[word=]"]
        for query in queries:
            with pytest.raises(BCQLSyntaxError) as exc_info:
                parse(query)
            assert exc_info.value.position < len(query), (
                f"position {exc_info.value.position} is past end of {query!r} (len={len(query)})"
            )

class TestTokenRepr:
    """Token __repr__ for debugging."""

    def test_repr(self):
        """Token repr includes type name, value, and position for debugging."""
        tok = Token(TokenType.IDENTIFIER, "word", 5)
        assert "IDENTIFIER" in repr(tok)
        assert "word" in repr(tok)
        assert "pos=5" in repr(tok)


class TestParseFromTokens:
    """The parse_from_tokens convenience function."""

    def test_basic(self):
        """``"however"`` - convenience function parses a pre-lexed token list into an AST."""
        tokens = BCQLLexer('"however"').tokenize()
        node = parse_from_tokens(tokens, source='"however"')
        assert isinstance(node, TokenQuery)
