"""Recursive descent parser for BCQL.

Starting from the lowest precedence operators and working down to the highest
precedence. The trick is that each level immediately delegates down to the
tighter-binding level before it looks for its own operator. This way we handle
precedence without needing separate left/right recursion or operator precedence
climbing.

Precedence chain (lowest -> highest), mirroring the BNF in ``bnf.md``::

    global_cst -> pos_filter -> rel_align -> union_intersect
    -> sequence -> capture -> span -> repetition -> atom

Within ``[...]`` brackets a separate, self-contained token-constraint
grammar applies (see ``_parse_token_expr`` and friends).
"""

from __future__ import annotations

from typing import Sequence

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.base import BCQLNode
from bcql_py.models.sequence import RepetitionNode, UnderscoreNode
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
        tokens: Token list produced by ``BCQLLexer``.
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
        """Build a ``BCQLSyntaxError`` pointing at the current token."""
        return BCQLSyntaxError(msg, bcql_query=self.source, error_position=self._current_token.position)

    def parse(self) -> BCQLNode:
        """Parse the token stream and return the root AST node.

        Raises:
            BCQLSyntaxError: On any syntax error.

        Returns:
            The root ``BCQLNode``.
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
            A ``BCQLNode``.
        """
        return self._parse_pos_filter()

    def _parse_pos_filter(self) -> BCQLNode:
        """``pos_filter := rel_align | pos_filter FILTER rel_align``

        Handles ``within``, ``containing``, ``overlap`` operators.
        Currently passes through; will be implemented in a later step.

        Returns:
            A ``BCQLNode``.
        """
        return self._parse_rel_align()

    def _parse_rel_align(self) -> BCQLNode:
        """``rel_align := union_intersect | union_intersect arrows | union_intersect aligns``

        Handles relation arrows (``-type->``) and alignment arrows
        (``=type=>``).  Currently passes through.

        Returns:
            A ``BCQLNode``.
        """
        return self._parse_union_intersect()

    def _parse_union_intersect(self) -> BCQLNode:
        """``union_intersect := sequence | union_intersect ('|' | '&') sequence``

        Handles sequence-level ``|`` (union) and ``&`` (intersection).
        Currently passes through; will be implemented in a later step.

        Returns:
            A ``BCQLNode``.
        """
        return self._parse_sequence()

    def _parse_sequence(self) -> BCQLNode:
        """``sequence := capture | capture sequence``

        Handles juxtaposition of tokens/sub-queries to form sequences.
        Currently passes through; will be implemented in a later step.

        Returns:
            A ``BCQLNode``.
        """
        return self._parse_capture()

    def _parse_capture(self) -> BCQLNode:
        """``capture := span | IDENT ':' capture``

        Handles named captures like ``A:[word="hello"]``.
        Currently passes through; will be implemented in a later step.

        Returns:
            A ``BCQLNode``.
        """
        return self._parse_span()

    def _parse_span(self) -> BCQLNode:
        """``span := repetition | '<' tag_name ... '>' | '</' tag_name '>'``

        Handles XML-style span queries.
        Currently passes through; will be implemented in a later step.

        Returns:
            A ``BCQLNode``.
        """
        return self._parse_repetition()

    def _parse_repetition(self) -> BCQLNode:
        """``repetition := atom | repetition quantifier``

        Parses the inner atom first, then greedily consumes any postfix
        quantifiers (``+``, ``*``, ``?``, ``{n}``, ``{n,m}``, ``{n,}``,
        ``{,m}``).  Multiple consecutive quantifiers each wrap the
        previous result in a new ``RepetitionNode``.

        The BNF rule is left-recursive (``repetition quantifier``), which
        we implement here as an iterative while-loop.  See
        ``010_token-based.md`` for repetition examples.

        Returns:
            The inner atom unchanged when no quantifier follows, or a
            ``RepetitionNode`` wrapping the atom.
        """
        node = self._parse_atom()

        while self._current_token_is_oneof(TokenType.PLUS, TokenType.STAR, TokenType.QUESTION, TokenType.LBRACE):
            tok = self._current_token

            if tok.type == TokenType.PLUS:
                self._advance()
                node = RepetitionNode(child=node, min_count=1, max_count=None)

            elif tok.type == TokenType.STAR:
                self._advance()
                node = RepetitionNode(child=node, min_count=0, max_count=None)

            elif tok.type == TokenType.QUESTION:
                self._advance()
                node = RepetitionNode(child=node, min_count=0, max_count=1)

            elif tok.type == TokenType.LBRACE:
                node = self._parse_brace_quantifier(node)

        return node

    def _parse_brace_quantifier(self, child: BCQLNode) -> RepetitionNode:
        """Parse a brace quantifier: ``{n}``, ``{n,m}``, ``{n,}``, or ``{,m}``.

        Called after the child node has been parsed and we see ``{``.

        Args:
            child: The node to which the quantifier applies.

        Returns:
            A ``RepetitionNode`` with the appropriate min/max counts.
        """
        self._expect(TokenType.LBRACE, "at start of brace quantifier")

        # {,m} - "up to m"
        if self._current_token.type == TokenType.COMMA:
            self._advance()
            max_tok = self._expect(TokenType.INTEGER, "as upper bound in {,m} quantifier")
            self._expect(TokenType.RBRACE, "at end of brace quantifier")
            return RepetitionNode(child=child, min_count=0, max_count=int(max_tok.value))

        min_tok = self._expect(TokenType.INTEGER, "as count in brace quantifier")
        min_val = int(min_tok.value)

        # {n} - exact count
        if self._current_token.type == TokenType.RBRACE:
            self._advance()
            return RepetitionNode(child=child, min_count=min_val, max_count=min_val)

        # {n, ...
        self._expect(TokenType.COMMA, "in brace quantifier")

        # {n,} - "n or more"
        if self._current_token.type == TokenType.RBRACE:
            self._advance()
            return RepetitionNode(child=child, min_count=min_val, max_count=None)

        # {n,m} - range
        max_tok = self._expect(TokenType.INTEGER, "as upper bound in {n,m} quantifier")
        self._expect(TokenType.RBRACE, "at end of brace quantifier")
        return RepetitionNode(child=child, min_count=min_val, max_count=int(max_tok.value))

    def _parse_atom(self) -> BCQLNode:
        """``atom := '[' token_expr? ']' | STRING | '_' | ...``

        The highest-precedence production in the sequence-level grammar.
        Currently handles token queries (``[...]``), bare string
        shorthands (``"man"``), and the underscore wildcard (``_``).

        Other atom alternatives (parenthesized groups, negation, root
        relations, lookarounds, functions) will be added in later steps.

        Returns:
            A ``TokenQuery`` for ``[...]``
            and bare strings, or an
            ``UnderscoreNode`` for ``_``.

        Raises:
            BCQLSyntaxError: When the current token cannot start an atom.
        """
        tok = self._current_token

        # --- Token query: [constraint]  or  [] ---
        if tok.type == TokenType.LBRACKET:
            return self._parse_token_query()

        # Bare string shorthand: "man" -> TokenQuery(shorthand=StringValue(...))
        if tok.type in (TokenType.STRING, TokenType.LITERAL_STRING):
            return self._parse_string_shorthand()

        # --- Underscore wildcard: _ ---
        if tok.type == TokenType.UNDERSCORE:
            self._advance()
            return UnderscoreNode()

        raise self._raise_error(f"Expected a token query, string, or '_', got {tok.type.name} ({tok.value!r})")

    def _parse_token_query(self) -> TokenQuery:
        """Parse a bracketed token query: ``[`` *token_expr*? ``]``.

        Produces an empty match-all ``TokenQuery(constraint=None)`` for
        ``[]``, or delegates to ``_parse_token_expr`` for the
        constraint inside brackets.

        Returns:
            A ``TokenQuery``.
        """
        self._expect(TokenType.LBRACKET, "at start of token query")

        # Empty brackets -> match-all
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
            A ``TokenQuery`` with ``shorthand``
            set to a ``StringValue``.
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
            A ``ConstraintExpr`` node.
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
            A ``BoolConstraint`` when an
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
            A ``NotConstraint`` when negated,
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
          Produces an ``AnnotationConstraint``.
        - **Integer range** (``pos_confidence=in[50,100]``):
          Produces an ``IntegerRangeConstraint``.
        - **Function/pseudo-annotation** (``word("man","woman")``):
          Produces a ``FunctionConstraint``.
          See ``010_token-based.md`` for details on pseudo-annotation
          functions (e.g. ``punctAfter``).
        - **Parenthesized sub-expression** (``(word="a" | word="the")``):
          Recurses into ``_parse_token_bool``.

        Returns:
            A ``ConstraintExpr`` node.

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
                f"Expected annotation name or '(' inside token constraint, got {tok.type.name} ({tok.value!r})"
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
            An ``AnnotationConstraint``.

        Raises:
            BCQLSyntaxError: When the value is not a string token.
        """
        tok = self._current_token
        if tok.type not in (TokenType.STRING, TokenType.LITERAL_STRING):
            raise self._raise_error(
                f"Expected a string value after {annotation!r}{operator}, got {tok.type.name} ({tok.value!r})"
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
            An ``IntegerRangeConstraint``.
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
            A ``FunctionConstraint``.
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
        """Consume a STRING or LITERAL_STRING token and return a ``StringValue``.

        Args:
            context: Human-readable context for the error message.

        Returns:
            A ``StringValue``.

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
        tokens: The list of tokens to parse (from ``tokenize``).
        source: The original source string.

    Returns:
        The root ``BCQLNode``.
    """
    parser = BCQLParser(tokens, source=source)
    return parser.parse()
