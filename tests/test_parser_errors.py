"""Tests for parser error reporting: syntax errors with position information."""

import pytest
from conftest import parse, round_trip

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.capture import AnnotationRef, GlobalConstraintNode
from bcql_py.models.token import NotConstraint, TokenQuery
from bcql_py.parser.parser import BCQLParser, parse_from_tokens
from bcql_py.parser.tokens import Token, TokenType


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


class TestParserConstructorValidation:
    """BCQLParser constructor rejects invalid token lists."""

    def test_empty_token_list(self):
        with pytest.raises(BCQLSyntaxError, match="No tokens"):
            BCQLParser([], source="")

    def test_missing_eof(self):
        tokens = [Token(TokenType.UNDERSCORE, "_", 0)]
        with pytest.raises(BCQLSyntaxError, match="end with EOF"):
            BCQLParser(tokens, source="_")

    def test_multiple_eof(self):
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
        with pytest.raises(BCQLSyntaxError, match="Unexpected token"):
            parse('"cat" ]')


class TestTagNameError:
    """Invalid tag name token raises an error."""

    def test_numeric_tag_name(self):
        with pytest.raises(BCQLSyntaxError, match="tag name"):
            parse("<42/>")


class TestTokenConstraintNonIdent:
    """Non-identifier where annotation name expected inside [...]."""

    def test_integer_inside_bracket(self):
        with pytest.raises(BCQLSyntaxError, match="annotation name"):
            parse("[42]")


class TestCaptureConstraintEdgeCases:
    """Edge cases in capture constraint parsing."""

    def test_bare_ident_in_cc(self):
        """Bare identifier in capture constraint acts as annotation ref."""
        node = parse('[word="cat"] :: A')
        assert isinstance(node, GlobalConstraintNode)
        cc = node.constraint
        assert isinstance(cc, AnnotationRef)
        assert cc.label == "A"
        assert cc.annotation == ""

    def test_invalid_token_in_cc(self):
        """Invalid token at start of capture constraint atom."""
        with pytest.raises(BCQLSyntaxError, match="capture constraint"):
            parse('[word="cat"] :: <')


class TestNotConstraintParenWrap:
    """NotConstraint wraps BoolConstraint operand in parens during to_bcql."""

    def test_not_bool_constraint_round_trip(self):
        round_trip('[!(word="a" & pos="N")]')

    def test_not_bool_constraint_structure(self):
        node = parse('[!(word="a" & pos="N")]')
        assert isinstance(node, TokenQuery)
        assert isinstance(node.constraint, NotConstraint)


class TestBcqlCachedProperty:
    """The .bcql cached property delegates to to_bcql()."""

    def test_bcql_property(self):
        node = parse('"cat"')
        assert node.bcql == node.to_bcql()


class TestTokenRepr:
    """Token __repr__ for debugging."""

    def test_repr(self):
        tok = Token(TokenType.IDENTIFIER, "word", 5)
        assert "IDENTIFIER" in repr(tok)
        assert "word" in repr(tok)
        assert "pos=5" in repr(tok)


class TestParseFromTokens:
    """The parse_from_tokens convenience function."""

    def test_basic(self):
        from bcql_py.parser.lexer import BCQLLexer

        tokens = list(BCQLLexer('"cat"').tokenize())
        node = parse_from_tokens(tokens, source='"cat"')
        assert isinstance(node, TokenQuery)
