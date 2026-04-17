from bcql_py.models.base import BCQLNode
from bcql_py.parser.lexer import BCQLLexer
from bcql_py.parser.parser import BCQLParser
from bcql_py.parser.tokens import Token, TokenType


def parse(source: str) -> BCQLNode:
    """Tokenize then parse a BCQL query string and return the root AST node.

    Args:
        source (str): The BCQL query to parse.

    Returns:
        BCQLNode: The root node of the parsed AST.
    """
    tokens = BCQLLexer(source).tokenize()
    return BCQLParser(tokens, source=source).parse()


__all__ = ["BCQLLexer", "BCQLParser", "Token", "TokenType", "parse"]
