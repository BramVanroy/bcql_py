"""Recursive descent parser for BCQL"""

from __future__ import annotations

import re

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.alignment import (
    AlignmentConstraint,
    AlignmentNode,
    AlignmentOperator,
)
from bcql_py.models.base import BCQLNode
from bcql_py.models.capture import (
    AnnotationRef,
    CaptureConstraintExpr,
    CaptureNode,
    ConstraintBoolean,
    ConstraintComparison,
    ConstraintFunctionCall,
    ConstraintLiteral,
    ConstraintNot,
    GlobalConstraintNode,
)
from bcql_py.models.function import FunctionCallNode
from bcql_py.models.lookaround import LookaheadNode, LookbehindNode
from bcql_py.models.relation import (
    ChildConstraint,
    RelationNode,
    RelationOperator,
    RootRelationNode,
)
from bcql_py.models.sequence import (
    GroupNode,
    IntersectionNode,
    NegationNode,
    RepetitionNode,
    SequenceNode,
    UnionNode,
    UnderscoreNode,
)
from bcql_py.models.span import PositionFilterNode, SpanQuery
from bcql_py.models.token import (
    AnnotationConstraint,
    BoolConstraint,
    ConstraintExpr,
    FunctionConstraint,
    IntegerRangeConstraint,
    NotConstraint,
    StringValue,
    TokenQuery,
)
from bcql_py.parser.tokens import Token, TokenType


class BCQLParser:
    """Parse a list of BCQL tokens into an AST.

    Args:
        tokens: Token list produced by [BCQLLexer][bcql_py.parser.lexer.BCQLLexer].
        source: The original query string (for error messages).
        schema: Optional corpus schema for annotation validation.
    """

    def __init__(
        self,
        tokens: list[Token],
        source: str = "",
    ) -> None:
        self.tokens = tokens
        self.source = source
        self.pos = 0

    @property
    def _current_token(self) -> Token:
        """Return the token at the current position."""
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        """Look ahead by *offset* tokens from current position."""
        idx = self.pos + offset
        return self.tokens[idx]

    def _current_token_is_oneof(self, *types: TokenType) -> bool:
        """Check if current token is one of the given types."""
        return self._current_token.type in types

    def _advance(self) -> Token:
        """Consume and return the current token, advancing the position."""
        tok = self._current_token
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _expect(self, ttype: TokenType, context: str = "") -> Token:
        """Consume the current token if it matches *ttype*, else error."""
        tok = self._current_token
        if tok.type != ttype:
            ctx = f" {context}" if context else ""
            raise BCQLSyntaxError(f"Expected {ttype.name}{ctx}, got {tok.type.name} ({tok.value!r})", query=self.source, position=tok.position)
        return self._advance()

    def _raise_error(self, msg: str) -> BCQLSyntaxError:
        return BCQLSyntaxError(msg, query=self.source, position=self._current_token.position)
