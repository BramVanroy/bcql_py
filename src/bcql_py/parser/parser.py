"""Recursive descent parser for BCQL.

Starting from the lowest precedence operators and working down to the highest
precedence. The trick is that each level immediately delegates down to the
tighter-binding level before it looks for its own operator. This way we handle
precedence without needing separate left/right recursion or operator precedence
climbing.

Precedence chain (lowest → highest), mirroring the BNF in ``bnf.md``::

    global_cst  →  pos_filter  →  rel_align  →  union_intersect
    →  sequence  →  capture  →  span  →  repetition  →  atom

Within ``[...]`` brackets a separate, self-contained token-constraint
grammar applies (see ``_parse_token_expr`` and friends).
"""

from __future__ import annotations
from typing import Sequence

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.base import BCQLNode
from bcql_py.models.sequence import UnderscoreNode
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
        tokens: Token list produced by :class:`~bcql_py.parser.lexer.BCQLLexer`.
        source: The original query string (used in error messages).
    """

    def __init__(self, tokens: Sequence[Token], source: str = "") -> None:
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
        """Consume the current token if it matches *ttype*, else raise.

        Args:
            ttype: The expected token type.
            context: Optional human-readable context for the error message
                (e.g. ``"inside token constraint"``).

        Raises:
            BCQLSyntaxError: When the current token does not match *ttype*.
        """
        tok = self._current_token
        if tok.type != ttype:
            ctx = f" {context}" if context else ""
            raise BCQLSyntaxError(
                f"Expected {ttype.name}{ctx}, got {tok.type.name} ({tok.value!r})",
                bcql_query=self.source,
                error_position=tok.position,
            )
        return self._advance()

    def _raise_error(self, msg: str) -> BCQLSyntaxError:
        """Build a :class:`BCQLSyntaxError` pointing at the current token."""
        return BCQLSyntaxError(msg, bcql_query=self.source, error_position=self._current_token.position)

    def parse(self) -> BCQLNode:
        """Parse the token stream and return the root AST node.

        Raises:
            BCQLSyntaxError: On any syntax error.

        Returns:
            The root :class:`~bcql_py.models.base.BCQLNode`.
        """
        node = self._parse_global_constraint()
        if not self._current_token_is_oneof(TokenType.EOF):
            tok = self._current_token
            raise self._raise_error(f"Unexpected token {tok.value!r} after end of query")
        return node

    def _parse_global_constraint(self) -> BCQLNode:
        """``global_cst := pos_filter | pos_filter '::' cc_expr``

        Lowest precedence level. Currently passes through; the ``::`` capture-constraint branch will be added in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_pos_filter()

    def _parse_pos_filter(self) -> BCQLNode:
        """``pos_filter := rel_align | pos_filter FILTER rel_align``

        Handles ``within``, ``containing``, ``overlap`` operators.
        Currently passes through; will be implemented in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_rel_align()

    def _parse_rel_align(self) -> BCQLNode:
        """``rel_align := union_intersect | union_intersect arrows | union_intersect aligns``

        Handles relation arrows (``-type->``) and alignment arrows
        (``=type=>``).  Currently passes through.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_union_intersect()

    def _parse_union_intersect(self) -> BCQLNode:
        """``union_intersect := sequence | union_intersect ('|' | '&') sequence``

        Handles sequence-level ``|`` (union) and ``&`` (intersection).
        Currently passes through; will be implemented in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_sequence()

    def _parse_sequence(self) -> BCQLNode:
        """``sequence := capture | capture sequence``

        Handles juxtaposition of tokens/sub-queries to form sequences.
        Currently passes through; will be implemented in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_capture()

    def _parse_capture(self) -> BCQLNode:
        """``capture := span | IDENT ':' capture``

        Handles named captures like ``A:[word="hello"]``.
        Currently passes through; will be implemented in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_span()

    def _parse_span(self) -> BCQLNode:
        """``span := repetition | '<' tag_name ... '>' | '</' tag_name '>'``

        Handles XML-style span queries.
        Currently passes through; will be implemented in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_repetition()

    def _parse_repetition(self) -> BCQLNode:
        """``repetition := atom | repetition quantifier``

        Handles quantifiers ``+``, ``*``, ``?``, ``{n}``, ``{n,m}``, etc.
        Currently passes through; will be implemented in a later step.

        Returns:
            A :class:`~bcql_py.models.base.BCQLNode`.
        """
        return self._parse_atom()

    def _parse_atom(self) -> BCQLNode:
        """``atom := '[' token_expr? ']' | STRING | '_' | ...``

        The highest-precedence production in the sequence-level grammar.
        Currently handles token queries (``[...]``), bare string
        shorthands (``"man"``), and the underscore wildcard (``_``).

        Other atom alternatives (parenthesized groups, negation, root
        relations, lookarounds, functions) will be added in later steps.

        Returns:
            A :class:`~bcql_py.models.token.TokenQuery` for ``[...]``
            and bare strings, or an
            :class:`~bcql_py.models.sequence.UnderscoreNode` for ``_``.

        Raises:
            BCQLSyntaxError: When the current token cannot start an atom.
        """
        tok = self._current_token

        # --- Token query: [constraint]  or  [] ---
        if tok.type == TokenType.LBRACKET:
            return self._parse_token_query()

        # --- Bare string shorthand: "man" → TokenQuery(shorthand=StringValue(...)) ---
        if tok.type in (TokenType.STRING, TokenType.LITERAL_STRING):
            return self._parse_string_shorthand()

        # --- Underscore wildcard: _ ---
        if tok.type == TokenType.UNDERSCORE:
            self._advance()
            return UnderscoreNode()

        raise self._raise_error(
            f"Expected a token query, string, or '_', got {tok.type.name} ({tok.value!r})"
        )

    def _parse_token_query(self) -> TokenQuery:
        """Parse a bracketed token query: ``[`` *token_expr*? ``]``.

        Produces an empty match-all ``TokenQuery(constraint=None)`` for
        ``[]``, or delegates to :meth:`_parse_token_expr` for the
        constraint inside brackets.

        Returns:
            A :class:`~bcql_py.models.token.TokenQuery`.
        """
        self._expect(TokenType.LBRACKET, "at start of token query")

        # Empty brackets → match-all
        if self._current_token.type == TokenType.RBRACKET:
            self._advance()
            return TokenQuery()

        constraint = self._parse_token_expr()
        self._expect(TokenType.RBRACKET, "at end of token query")
        return TokenQuery(constraint=constraint)

    def _parse_string_shorthand(self) -> TokenQuery:
        """Parse a bare string like ``"man"`` as a token-query shorthand.

        Per the BCQL spec, a bare string is shorthand for
        ``[<default_annotation>="..."]``. The parser stores it as a
        ``TokenQuery`` with the ``shorthand`` field set so that the
        original surface form is preserved during round-tripping.
        See ``010_token-based.md`` for details on the default annotation
        convention.

        Returns:
            A :class:`~bcql_py.models.token.TokenQuery` with ``shorthand``
            set to a :class:`~bcql_py.models.token.StringValue`.
        """
        tok = self._advance()
        sv = StringValue(
            value=tok.value,
            is_literal=(tok.type == TokenType.LITERAL_STRING),
        )
        return TokenQuery(shorthand=sv)

    def _parse_token_expr(self) -> ConstraintExpr:
        """``token_expr := token_bool``

        Entry point for the token-constraint grammar used inside ``[...]``.

        Returns:
            A :data:`~bcql_py.models.token.ConstraintExpr` node.
        """
        return self._parse_token_bool()

    def _parse_token_bool(self) -> ConstraintExpr:
        """``token_bool := token_not | token_bool ('|' | '&') token_not``

        Left-associative boolean combination.  Both ``&`` and ``|`` share
        the **same** precedence at every grammar level (token constraints,
        sequence-level, and capture constraints).  This is intentional in
        CQL and differs from standard boolean conventions.  See ``bnf.md``
        and the ``booleanOperator`` rule in ``Bcql.g4``.

        Returns:
            A :class:`~bcql_py.models.token.BoolConstraint` when an
            operator is present, otherwise the inner constraint unchanged.
        """
        left = self._parse_token_not()

        while self._current_token_is_oneof(TokenType.AMP, TokenType.PIPE):
            op_tok = self._advance()
            operator: str = "&" if op_tok.type == TokenType.AMP else "|"
            right = self._parse_token_not()
            left = BoolConstraint(operator=operator, left=left, right=right)

        return left

    def _parse_token_not(self) -> ConstraintExpr:
        """``token_not := token_cmp | '!' token_not``

        Prefix negation inside token constraints.  Recursively handles
        chained negations like ``!!expr`` (though unusual in practice).

        Returns:
            A :class:`~bcql_py.models.token.NotConstraint` when negated,
            otherwise the inner constraint unchanged.
        """
        if self._current_token.type == TokenType.BANG:
            self._advance()
            operand = self._parse_token_not()
            return NotConstraint(operand=operand)

        return self._parse_token_cmp()

    def _parse_token_cmp(self) -> ConstraintExpr:
        """``token_cmp := IDENT ('=' | '!=') STRING``
        ``           | IDENT '=' 'in' '[' INT ',' INT ']'``
        ``           | IDENT '(' string_list ')'``
        ``           | '(' token_bool ')'``

        Highest-precedence level inside token constraints.  Dispatches
        based on the tokens following the identifier:

        - **Annotation comparison** (``word="man"``, ``pos!="noun"``):
          Produces an :class:`~bcql_py.models.token.AnnotationConstraint`.
        - **Integer range** (``pos_confidence=in[50,100]``):
          Produces an :class:`~bcql_py.models.token.IntegerRangeConstraint`.
        - **Function/pseudo-annotation** (``word("man","woman")``):
          Produces a :class:`~bcql_py.models.token.FunctionConstraint`.
          See ``010_token-based.md`` for details on pseudo-annotation
          functions (e.g. ``punctAfter``).
        - **Parenthesized sub-expression** (``(word="a" | word="the")``):
          Recurses into :meth:`_parse_token_bool`.

        Returns:
            A :data:`~bcql_py.models.token.ConstraintExpr` node.

        Raises:
            BCQLSyntaxError: On unexpected tokens inside brackets.
        """
        tok = self._current_token

        # --- Parenthesized sub-expression ---
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_token_bool()
            self._expect(TokenType.RPAREN, "inside token constraint")
            return expr

        # --- Identifier-led alternatives ---
        if tok.type != TokenType.IDENTIFIER:
            raise self._raise_error(
                f"Expected annotation name or '(' inside token constraint, "
                f"got {tok.type.name} ({tok.value!r})"
            )

        ident_tok = self._advance()
        annotation = ident_tok.value

        # Function call: ident '(' string_list ')'
        if self._current_token.type == TokenType.LPAREN:
            return self._parse_function_constraint(annotation)

        # Comparison: ident ('=' | '!=') ...
        if self._current_token.type == TokenType.EQ:
            self._advance()

            # Integer range: ident '=' 'in' '[' INT ',' INT ']'
            if self._current_token.type == TokenType.IN:
                return self._parse_integer_range_constraint(annotation)

            # Normal annotation comparison: ident '=' STRING
            return self._parse_annotation_value(annotation, "=")

        if self._current_token.type == TokenType.NEQ:
            self._advance()
            return self._parse_annotation_value(annotation, "!=")

        raise self._raise_error(
            f"Expected '=', '!=', or '(' after annotation name {annotation!r}, "
            f"got {self._current_token.type.name} ({self._current_token.value!r})"
        )

    def _parse_annotation_value(self, annotation: str, operator: str) -> AnnotationConstraint:
        """Parse the string value after ``annotation =`` or ``annotation !=``.

        Handles both regular strings (``"man"``) and literal strings
        (``l"e.g."``).  See ``010_token-based.md`` for discussion of
        literal strings and regex escaping.

        Args:
            annotation: The annotation name (e.g. ``"word"``).
            operator: ``"="`` or ``"!="``.

        Returns:
            An :class:`~bcql_py.models.token.AnnotationConstraint`.

        Raises:
            BCQLSyntaxError: When the value is not a string token.
        """
        tok = self._current_token
        if tok.type not in (TokenType.STRING, TokenType.LITERAL_STRING):
            raise self._raise_error(
                f"Expected a string value after {annotation!r}{operator}, "
                f"got {tok.type.name} ({tok.value!r})"
            )
        self._advance()
        sv = StringValue(
            value=tok.value,
            is_literal=(tok.type == TokenType.LITERAL_STRING),
        )
        return AnnotationConstraint(annotation=annotation, operator=operator, value=sv)

    def _parse_integer_range_constraint(self, annotation: str) -> IntegerRangeConstraint:
        """Parse ``'in' '[' INT ',' INT ']'`` after ``annotation =``.

        Example: ``pos_confidence=in[50,100]``.

        Args:
            annotation: The annotation name preceding ``=in[``.

        Returns:
            An :class:`~bcql_py.models.token.IntegerRangeConstraint`.
        """
        self._expect(TokenType.IN, "in integer range constraint")
        self._expect(TokenType.LBRACKET, "in integer range constraint")
        min_tok = self._expect(TokenType.INTEGER, "as lower bound of integer range")
        self._expect(TokenType.COMMA, "in integer range constraint")
        max_tok = self._expect(TokenType.INTEGER, "as upper bound of integer range")
        self._expect(TokenType.RBRACKET, "in integer range constraint")
        return IntegerRangeConstraint(
            annotation=annotation,
            min_val=int(min_tok.value),
            max_val=int(max_tok.value),
        )

    def _parse_function_constraint(self, name: str) -> FunctionConstraint:
        """Parse ``'(' string_list ')'`` after a function/pseudo-annotation name.

        Example: ``word("man", "woman")`` or ``punctAfter(",")``.
        See ``010_token-based.md`` for the pseudo-annotation convention
        where ``[punctAfter=","]`` is syntactic sugar for
        ``[punctAfter(",")]``.

        Args:
            name: The function name preceding ``(``.

        Returns:
            A :class:`~bcql_py.models.token.FunctionConstraint`.
        """
        self._expect(TokenType.LPAREN, "in function constraint")
        args: list[StringValue] = []

        if self._current_token.type != TokenType.RPAREN:
            args.append(self._parse_string_value("as function argument"))
            while self._current_token.type == TokenType.COMMA:
                self._advance()
                args.append(self._parse_string_value("as function argument"))

        self._expect(TokenType.RPAREN, "in function constraint")
        return FunctionConstraint(name=name, args=args)

    def _parse_string_value(self, context: str = "") -> StringValue:
        """Consume a STRING or LITERAL_STRING token and return a :class:`StringValue`.

        Args:
            context: Human-readable context for the error message.

        Returns:
            A :class:`~bcql_py.models.token.StringValue`.

        Raises:
            BCQLSyntaxError: When the current token is not a string.
        """
        tok = self._current_token
        if tok.type not in (TokenType.STRING, TokenType.LITERAL_STRING):
            ctx = f" {context}" if context else ""
            raise self._raise_error(f"Expected a string{ctx}, got {tok.type.name} ({tok.value!r})")
        self._advance()
        return StringValue(
            value=tok.value,
            is_literal=(tok.type == TokenType.LITERAL_STRING),
        )


def parse_from_tokens(tokens: list[Token], source: str) -> BCQLNode:
    """Parse a BCQL token list into an AST.

    Args:
        tokens: The list of tokens to parse (from :func:`~bcql_py.parser.lexer.tokenize`).
        source: The original source string.

    Returns:
        The root :class:`~bcql_py.models.base.BCQLNode`.
    """
    parser = BCQLParser(tokens, source=source)
    return parser.parse()
