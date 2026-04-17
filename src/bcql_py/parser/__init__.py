from functools import lru_cache
from typing import Sequence

from bcql_py.models.base import BCQLNode
from bcql_py.parser.lexer import BCQLLexer
from bcql_py.parser.parser import BCQLParser
from bcql_py.parser.tokens import Token, TokenType


@lru_cache(maxsize=64)
def tokenize(source: str) -> tuple[Token, ...]:
    """Tokenize a BCQL query string into a tuple of Tokens.

    Args:
        source (str): The BCQL query to tokenize.

    Returns:
        tuple[Token, ...]: The tuple of tokens.
    """
    lexer = BCQLLexer(source)
    return lexer.tokenize()


@lru_cache(maxsize=64)
def parse(source: str) -> BCQLNode:
    """Tokenize then parse a BCQL query string and return the root AST node.

    Args:
        source (str): The BCQL query to parse.

    Returns:
        BCQLNode: The root node of the parsed AST.
    """
    tokens = BCQLLexer(source).tokenize()
    return BCQLParser(tokens, source=source).parse()


@lru_cache(maxsize=64)
def parse_from_tokens(tokens: Sequence[Token], source: str) -> BCQLNode:
    """Parse a BCQL token list into an abstract syntax tree.

    Args:
        tokens: The list of tokens to parse (from ``tokenize``).
        source: The original source string.

    Returns:
        The root ``BCQLNode``.
    """
    parser = BCQLParser(tokens, source=source)
    return parser.parse()


__all__ = ["BCQLLexer", "BCQLParser", "Token", "TokenType", "tokenize", "parse", "parse_from_tokens"]
