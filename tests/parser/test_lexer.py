import pytest

from bcql_py.parser.lexer import BCQLLexer, BCQLSyntaxError
from bcql_py.parser.tokens import Token, TokenType


def lex(source: str) -> list[Token]:
    """Tokenize *source* and return tokens (excl. EOF)."""
    tokens = BCQLLexer(source).tokenize()
    tokens = [token for token in tokens if token.type != TokenType.EOF]
    return tokens


class TestLexerStrings:
    def test_double_quoted(self):
        tokens = lex('"hello"')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"

    def test_single_quoted(self):
        tokens = lex("'hello'")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"

    def test_literal_string(self):
        tokens = lex('l"e.g."')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LITERAL_STRING
        # Note that the 'l' prefix is not included in the token value! It's just a marker for the lexer to treat the string as literal.
        # The full string content, including any escaped characters, is stored in the token value.
        assert tokens[0].value == "e.g."

    def test_escaped_quote(self):
        tokens = lex('"say \\"yes\\""')
        assert tokens[0].value == 'say \\"yes\\"'

    def test_regex_in_string(self):
        tokens = lex('"(wo)?man"')
        assert tokens[0].value == "(wo)?man"

    def test_sensitivity_flags(self):
        tokens = lex('"(?-i)Panama"')
        assert tokens[0].value == "(?-i)Panama"


class TestLexerIdentifiers:
    def test_simple_identifier(self):
        tokens = lex("lemma")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "lemma"

    def test_keyword_within(self):
        tokens = lex("within")
        assert tokens[0].type == TokenType.WITHIN

    def test_keyword_containing(self):
        tokens = lex("containing")
        assert tokens[0].type == TokenType.CONTAINING

    def test_keyword_overlap(self):
        tokens = lex("overlap")
        assert tokens[0].type == TokenType.OVERLAP

    def test_keyword_in(self):
        tokens = lex("in")
        assert tokens[0].type == TokenType.IN

    def test_keyword_true(self):
        tokens = lex("true")
        assert tokens[0].type == TokenType.TRUE

    def test_keyword_false(self):
        tokens = lex("false")
        assert tokens[0].type == TokenType.FALSE

    def test_keyword_underscore(self):
        tokens = lex("_")
        assert tokens[0].type == TokenType.UNDERSCORE
        assert tokens[0].value == "_"


class TestLexerBrackets:
    def test_square_brackets(self):
        tokens = lex("[]")
        assert tokens[0].type == TokenType.LBRACKET
        assert tokens[1].type == TokenType.RBRACKET

    def test_parens(self):
        tokens = lex("()")
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.RPAREN

    def test_curly_brackets(self):
        tokens = lex("{}")
        assert tokens[0].type == TokenType.LBRACE
        assert tokens[1].type == TokenType.RBRACE


class TestLexerLookaround:
    def test_positive_lookahead(self):
        tokens = lex("(?=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKAHEAD_POS

    def test_negative_lookahead(self):
        tokens = lex("(?!")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKAHEAD_NEG

    def test_positive_lookbehind(self):
        tokens = lex("(?<=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKBEHIND_POS

    def test_negative_lookbehind(self):
        tokens = lex("(?<!")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKBEHIND_NEG


class TestLexerXML:
    def test_lt(self):
        tokens = lex("<")
        assert tokens[0].type == TokenType.LT

    def test_lt_slash(self):
        tokens = lex("</")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LT_SLASH

    def test_gt(self):
        tokens = lex(">")
        assert tokens[0].type == TokenType.GT

    def test_slash_gt(self):
        tokens = lex("/>")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.SLASH_GT


class TestLexerArrows:
    def test_rel_arrow(self):
        tokens = lex("-obj->")
        assert tokens[0].type == TokenType.REL_LINE
        assert tokens[0].value == "-"

        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "obj"

        assert tokens[2].type == TokenType.REL_ARROW
        assert tokens[2].value == "->"

    def test_root_rel_arrow(self):
        tokens = lex("^-obj->")
        assert tokens[0].type == TokenType.ROOT_REL_CARET
        assert tokens[0].value == "^"

        assert tokens[1].type == TokenType.REL_LINE
        assert tokens[1].value == "-"

        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "obj"

        assert tokens[3].type == TokenType.REL_ARROW
        assert tokens[3].value == "->"

    def test_untyped_rel_arrow(self):
        tokens = lex("-->")
        assert tokens[0].type == TokenType.REL_LINE
        assert tokens[0].value == "-"

        assert tokens[1].type == TokenType.REL_ARROW
        assert tokens[1].value == "->"

    def test_untyped_root_rel_arrow(self):
        tokens = lex("^-->")
        assert tokens[0].type == TokenType.ROOT_REL_CARET
        assert tokens[0].value == "^"

        assert tokens[1].type == TokenType.REL_LINE
        assert tokens[1].value == "-"

        assert tokens[2].type == TokenType.REL_ARROW
        assert tokens[2].value == "->"

    def test_untyped_align_arrow(self):
        tokens = lex("==>nl")
        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[0].value == "="

        assert tokens[1].type == TokenType.ALIGN_ARROW
        assert tokens[1].value == "=>"

        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "nl"

    def test_untyped_optional_align_arrow(self):
        tokens = lex("==>nl?")
        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[0].value == "="

        assert tokens[1].type == TokenType.ALIGN_ARROW
        assert tokens[1].value == "=>"

        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "nl"

        assert tokens[3].type == TokenType.QUESTION
        assert tokens[3].value == "?"

    def test_align_arrow(self):
        tokens = lex("=word=>nl")

        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[0].value == "="

        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "word"

        assert tokens[2].type == TokenType.ALIGN_ARROW
        assert tokens[2].value == "=>"

        assert tokens[3].type == TokenType.IDENTIFIER
        assert tokens[3].value == "nl"


class TestLexerIntegers:
    def test_positive(self):
        tokens = lex("42")
        assert tokens[0].type == TokenType.INTEGER
        assert tokens[0].value == "42"

    def test_negative(self):
        tokens = lex("-5")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.INTEGER
        assert tokens[0].value == "-5"


class TestLexerOperators:
    def test_equals(self):
        tokens = lex("=")
        assert tokens[0].type == TokenType.EQ
        assert tokens[0].value == "="

    def test_not_equals(self):
        tokens = lex("!=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.NEQ
        assert tokens[0].value == "!="

    def test_less_than(self):
        tokens = lex("<")
        assert tokens[0].type == TokenType.LT
        assert tokens[0].value == "<"

    def test_less_equal(self):
        tokens = lex("<=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LTE
        assert tokens[0].value == "<="

    def test_greater_than(self):
        tokens = lex(">")
        assert tokens[0].type == TokenType.GT
        assert tokens[0].value == ">"

    def test_greater_equal(self):
        # Lexer tokenizes >= as two separate tokens: GT + EQ
        tokens = lex(">=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.GTE
        assert tokens[0].value == ">="

    def test_bang(self):
        tokens = lex("!")
        assert tokens[0].type == TokenType.BANG

    def test_ampersand(self):
        tokens = lex("&")
        assert tokens[0].type == TokenType.AMP

    def test_pipe(self):
        tokens = lex("|")
        assert tokens[0].type == TokenType.PIPE

    def test_single_colon(self):
        tokens = lex(":")
        assert tokens[0].type == TokenType.COLON
        assert tokens[0].value == ":"

    def test_double_colon(self):
        tokens = lex("::")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.DOUBLE_COLON
        assert tokens[0].value == "::"

    def test_semicolon(self):
        tokens = lex(";")
        assert tokens[0].type == TokenType.SEMICOLON
        assert tokens[0].value == ";"

    def test_dot(self):
        tokens = lex(".")
        assert tokens[0].type == TokenType.DOT
        assert tokens[0].value == "."

    def test_comma(self):
        tokens = lex(",")
        assert tokens[0].type == TokenType.COMMA
        assert tokens[0].value == ","


class TestLexerComments:
    def test_single_comment_ignored(self):
        tokens = lex('"man" # this is a comment')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "man"

    def test_multiline_comment_ignored(self):
        query = """"man" /* this is a
        multiline comment */"""
        tokens = lex(query)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "man"


class TestLexerPositions:
    def test_position_tracking(self):
        tokens = BCQLLexer('[word="man"]').tokenize()
        assert tokens[0].position == 0
        assert tokens[1].position == 1
        assert tokens[2].position == 5
        assert tokens[3].position == 6
        assert tokens[4].position == 11
        assert tokens[5].position == 12


class TestLexerErrors:
    def test_unclosed_string(self):
        with pytest.raises(BCQLSyntaxError):
            BCQLLexer('"unclosed').tokenize()
