from functools import lru_cache
from typing import Sequence

from bcql_py.models.base import BCQLNode
from bcql_py.parser.lexer import BCQLLexer
from bcql_py.parser.parser import BCQLParser
from bcql_py.parser.tokens import Token, TokenType
from bcql_py.validation.spec import CorpusSpec
from bcql_py.validation.validator import validate as _validate


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
def _parse_cached(source: str) -> BCQLNode:
    tokens = BCQLLexer(source).tokenize()
    return BCQLParser(tokens, source=source).parse()


def parse(source: str, *, spec: CorpusSpec | None = None, fail_fast: bool = True) -> BCQLNode:
    """Tokenize then parse a BCQL query string and return the root AST node.

    When *spec* is given, the parsed AST is additionally run through
    :func:`bcql_py.validation.validate` so that any corpus-specific semantic
    problems are surfaced immediately rather than at query-execution time.

    Args:
        source: The BCQL query to parse.
        spec: Optional :class:`~bcql_py.validation.CorpusSpec` describing the
            target corpus. When provided, semantic validation runs after a
            successful parse.
        fail_fast: Forwarded to :func:`bcql_py.validation.validate`; only has
            an effect when *spec* is provided. ``True`` raises on the first
            validation issue, ``False`` collects every issue before raising.

    Returns:
        The root :class:`~bcql_py.models.base.BCQLNode` of the parsed AST.

    Raises:
        BCQLSyntaxError: If the query cannot be parsed.
        BCQLValidationError: If *spec* is provided and the AST violates it.
    """
    ast = _parse_cached(source)
    if spec is not None:
        _validate(ast, spec, fail_fast=fail_fast)
    return ast


def parse_from_tokens(
    tokens: Sequence[Token],
    source: str,
    *,
    spec: CorpusSpec | None = None,
    fail_fast: bool = True,
) -> BCQLNode:
    """Parse a BCQL token list into an abstract syntax tree.

    Args:
        tokens: The list of tokens to parse (from ``tokenize``).
        source: The original source string.
        spec: Optional :class:`~bcql_py.validation.CorpusSpec`; see :func:`parse`.
        fail_fast: Forwarded to :func:`bcql_py.validation.validate` when *spec*
            is provided.

    Returns:
        The root ``BCQLNode``.
    """
    parser = BCQLParser(tokens, source=source)
    ast = parser.parse()
    if spec is not None:
        _validate(ast, spec, fail_fast=fail_fast)
    return ast


__all__ = ["BCQLLexer", "BCQLParser", "Token", "TokenType", "tokenize", "parse", "parse_from_tokens"]
