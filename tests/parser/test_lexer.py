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
