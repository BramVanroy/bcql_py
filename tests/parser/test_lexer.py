from bcql_py.parser.lexer import BCQLLexer
from bcql_py.parser.tokens import Token, TokenType


def lex(source: str) -> list[Token]:
    """Tokenize *source* and return tokens."""
    tokens = BCQLLexer(source).tokenize()
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

    def test_literal_string(self):
        tokens = lex('l"e.g."')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LITERAL_STRING
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


class TestLexerBrackets:
    def test_square_brackets(self):
        tokens = lex("[]")
        assert tokens[0].type == TokenType.LBRACKET
        assert tokens[1].type == TokenType.RBRACKET

    def test_parens(self):
        tokens = lex("()")
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.RPAREN


class TestLexerLookaround:
    def test_positive_lookahead(self):
        tokens = lex("(?=")
        assert tokens[0].type == TokenType.LOOKAHEAD_POS

    def test_negative_lookahead(self):
        tokens = lex("(?!")
        assert tokens[0].type == TokenType.LOOKAHEAD_NEG

    def test_positive_lookbehind(self):
        tokens = lex("(?<=")
        assert tokens[0].type == TokenType.LOOKBEHIND_POS

    def test_negative_lookbehind(self):
        tokens = lex("(?<!")
        assert tokens[0].type == TokenType.LOOKBEHIND_NEG


class TestLexerXML:
    def test_lt(self):
        tokens = lex("<")
        assert tokens[0].type == TokenType.LT

    def test_lt_slash(self):
        tokens = lex("</")
        assert tokens[0].type == TokenType.LT_SLASH

    def test_gt(self):
        tokens = lex(">")
        assert tokens[0].type == TokenType.GT

    def test_slash_gt(self):
        tokens = lex("/>")
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
    def test_negative(self):
        tokens = lex("-5")
        assert tokens[0].type == TokenType.INTEGER
        assert tokens[0].value == "-5"
