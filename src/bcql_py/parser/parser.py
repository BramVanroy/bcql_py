"""Recursive descent parser for BCQL.

Starting from the lowest precedence operators and working down to the highest. The trick is that each level
immediately delegates down to the tighter-binding level before it looks for its own operator, so while you start
at the lowest precedence, it is in fact materialized latest.

See bnf.md for the grammar that we're implementing.
"""

from __future__ import annotations

from typing import Sequence


__all__ = ["BCQLParser"]

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.alignment import AlignmentConstraint, AlignmentNode, AlignmentOperator
from bcql_py.models.base import BCQLNode
from bcql_py.models.capture import (
    AnnotationRef,
    CaptureNode,
    ConstraintBoolean,
    ConstraintComparison,
    ConstraintFunctionCall,
    ConstraintInteger,
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
    NegationNode,
    RepetitionNode,
    SequenceBoolNode,
    SequenceNode,
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
from bcql_py.parser.tokens import BOOL_OPS, CMP_OPS, Token, TokenType, display_token, display_type


class BCQLParser:
    """Parse a list of BCQL tokens into an AST.

    Args:
        tokens: Token sequence produced by ``BCQLLexer``
        source: The original query string (used in error messages).
    """

    __slots__ = ("_source", "_pos", "_tokens", "_ast")

    def __init__(self, tokens: Sequence[Token], source: str = "") -> None:
        self._source = source
        self._pos = 0
        self._tokens = tuple(tokens)
        self._ast: BCQLNode | None = None

        if not self._tokens:
            raise BCQLSyntaxError("No tokens to parse", bcql_query=source)
        if self._tokens[-1].type != TokenType.EOF:
            raise BCQLSyntaxError("Token list must end with EOF", bcql_query=source)
        if sum(1 for t in self._tokens if t.type == TokenType.EOF) > 1:
            raise BCQLSyntaxError("Token list must contain exactly one EOF", bcql_query=source)

    @property
    def source(self) -> str:
        return self._source

    @property
    def pos(self) -> int:
        return self._pos

    @property
    def tokens(self) -> tuple[Token, ...]:
        return self._tokens

    @property
    def ast(self) -> BCQLNode:
        """Parse the token stream and return the root AST node."""
        if self._ast is None:
            self.parse()
        return self._ast

    @property
    def _current_token(self) -> Token:
        """Return the token at the current position"""
        return self._tokens[self._pos]

    def _peek(self, offset: int = 0) -> Token:
        """Look ahead by *offset* tokens from current position."""
        idx = self._pos + offset
        return self._tokens[idx]

    def _current_token_is_oneof(self, *types: TokenType) -> bool:
        """Check if current token is one of the given types."""
        return self._current_token.type in types

    def _advance(self) -> Token:
        """Consume and return the current token, advancing the position."""
        tok = self._current_token
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _expect(self, ttype: TokenType, context: str = "") -> Token:
        """Consume the current token if it matches *ttype*, else raise.

        Args:
            ttype: The expected token type.
            context: Optional human-readable context for the error message (e.g. ``"inside token constraint"``).

        Raises:
            BCQLSyntaxError: When the current token does not match *ttype*.
        """
        tok = self._current_token
        if tok.type != ttype:
            ctx = f" {context}" if context else ""
            raise BCQLSyntaxError(
                f"Expected {display_type(ttype)}{ctx}, got {display_token(tok)}",
                bcql_query=self._source,
                error_position=tok.position,
            )
        return self._advance()

    def _raise_error(self, msg: str) -> BCQLSyntaxError:
        """Build a ``BCQLSyntaxError`` pointing at the current token."""
        return BCQLSyntaxError(msg, bcql_query=self._source, error_position=self._current_token.position)

    def parse(self, force_reparse: bool = False) -> BCQLNode:
        """Parse the token stream and return the root AST node. Sets ``self._ast`` to the result for caching.

        Args:
            force_reparse: If ``True``, forces reparsing even if an AST is already cached. This allows retrying
              after a syntax error without creating a new parser instance. Should rarely be needed.

        Raises:
            BCQLSyntaxError: On any syntax error.

        Returns:
            The root ``BCQLNode``.
        """
        if self._ast is not None and not force_reparse:
            return self._ast  # Return cached AST if already parsed

        self._ast = None  # Clear the cached AST before parsing to allow retrying after an error

        node = self._parse_global_constraint()
        if not self._current_token_is_oneof(TokenType.EOF):
            tok = self._current_token
            raise self._raise_error(f"Unexpected token {tok.value!r} after end of query")
        self._ast = node
        return node

    def _parse_global_constraint(self) -> BCQLNode:
        """``global_cst := pos_filter ('::' cc_expr)*``

        Lowest precedence level. When ``::`` is present, wraps the body and each capture
        constraint in a ``GlobalConstraintNode``. Multiple ``::`` are left-associative per
        ``Bcql.g4``'s ``constrainedQuery`` rule.

        Returns:
            A ``GlobalConstraintNode`` when ``::`` is present, otherwise the inner query unchanged.
        """
        body = self._parse_pos_filter()

        while self._current_token.type == TokenType.DOUBLE_COLON:
            self._advance()
            constraint = self._parse_cc_bool()
            body = GlobalConstraintNode(body=body, constraint=constraint)

        return body

    _FILTER_OPS = {TokenType.WITHIN, TokenType.CONTAINING, TokenType.OVERLAP}

    def _parse_pos_filter(self) -> BCQLNode:
        """``pos_filter := rel_align | rel_align FILTER pos_filter``

        Handles ``within``, ``containing``, ``overlap`` operators. Right-recursive per
        ``Bcql.g4``'s ``containingWithinQuery`` rule, so ``A within B within C`` parses
        as ``A within (B within C)``.

        Note that the grammar does not specify case-sensitivity, so we accept any case for the operators and normalise to lowercase in the AST.

        Returns:
            A ``PositionFilterNode`` when a filter operator is present, otherwise the inner
            ``rel_align`` unchanged.
        """
        left = self._parse_rel_align()

        if self._current_token.type in self._FILTER_OPS:
            op_tok = self._advance()
            right = self._parse_pos_filter()  # right-recursive
            return PositionFilterNode(operator=op_tok.value.lower(), left=left, right=right)

        return left

    def _parse_rel_align(self) -> BCQLNode:
        """``rel_align := sequence_bool | sequence_bool child_rel (';' child_rel)* | sequence_bool align_child (';' align_child)*``

        After parsing the source query, checks for child relation arrows (``-type->``) or
        negated relation arrows (``!-type->``), then for alignment arrows (``=type=>``). Multiple
        children/alignments are chained with ``;``. Both are right-recursive: the target of each
        child is a full ``_parse_rel_align``.

        Child relations and alignment arrows are kept in separate alternatives per our BNF, so
        mixing them in the same ``;``-chain is not allowed (see ``questions.md`` Q3).

        Returns:
            A ``RelationNode``, ``AlignmentNode``, or the source unchanged.
        """
        source = self._parse_sequence_bool()

        if self._starts_child_relation():
            children = [self._parse_child_relation()]
            while self._current_token.type == TokenType.SEMICOLON:
                self._advance()
                children.append(self._parse_child_relation())
            return RelationNode(source=source, children=children)

        if self._starts_alignment():
            alignments = [self._parse_alignment_child()]
            while self._current_token.type == TokenType.SEMICOLON:
                self._advance()
                alignments.append(self._parse_alignment_child())
            return AlignmentNode(source=source, alignments=alignments)

        return source

    def _starts_child_relation(self) -> bool:
        """Check if the current position begins a child relation arrow.

        A child relation starts with either ``REL_LINE`` (for ``-type->``) or ``BANG REL_LINE``
        (for ``!-type->``). We also handle an optional capture label prefix: ``IDENT ':' [!] -type->``.

        The ``BANG`` lookahead distinguishes negated relations from negated spans: at this level,
        ``BANG`` followed by ``REL_LINE`` is always a negated relation.

        Returns:
            ``True`` if a child relation arrow follows.
        """
        tok = self._current_token
        # Direct arrow: -type->
        if tok.type == TokenType.REL_LINE:
            return True
        # Negated arrow: !-type->
        if tok.type == TokenType.BANG and self._peek(1).type == TokenType.REL_LINE:
            return True
        # Capture label prefix: label:-type-> or label:!-type->
        if tok.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            after_colon = self._peek(2).type
            if after_colon == TokenType.REL_LINE:
                return True
            if after_colon == TokenType.BANG and self._peek(3).type == TokenType.REL_LINE:
                return True
        return False

    def _parse_child_relation(self) -> ChildConstraint:
        """``child_rel := [IDENT ':'] relation_op rel_align``

        Parses a single child constraint: optional capture label, a relation operator, and the
        target sub-query. The target is a full ``_parse_rel_align`` (right-recursive) so that
        ``_ -nsubj-> _ -amod-> _`` parses as ``_ -nsubj-> (_ -amod-> _)``.

        Returns:
            A ``ChildConstraint``.
        """
        label = None
        if self._current_token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            label = self._advance().value
            self._advance()  # consume ':'

        operator = self._parse_relation_operator()
        target = self._parse_rel_align()
        return ChildConstraint(operator=operator, target=target, label=label)

    def _parse_relation_operator(self) -> RelationOperator:
        """``relation_op := [!] '-' IDENT? '->' IDENT?``

        Parses the operator tokens that the lexer decomposed from a single arrow like ``-obj->``
        or ``!-nsubj->corrected``. The lexer emits the constituent tokens:
        ``[BANG] REL_LINE [IDENT] REL_ARROW [IDENT]``.

        Returns:
            A ``RelationOperator`` with type, negation flag, and optional target field.
        """
        negated = False
        if self._current_token.type == TokenType.BANG:
            negated = True
            self._advance()

        self._expect(TokenType.REL_LINE, "at start of relation arrow")

        relation_type = None
        if self._current_token.type == TokenType.IDENTIFIER:
            relation_type = self._advance().value

        self._expect(TokenType.REL_ARROW, "in relation arrow")

        target_field = None
        if self._current_token.type == TokenType.IDENTIFIER and not self._starts_child_relation():
            # Only consume IDENT as target field if it's not the start of IDENT ':' (a capture label
            # for the next child relation). We need this check because in ``_ -obj->field A:-amod-> _``
            # the IDENT after ``->`` is a target field only if it's NOT followed by ``:``.
            # But actually, target fields don't use ``:`` so: peek for ``IDENT COLON``
            if self._peek(1).type != TokenType.COLON:
                target_field = self._advance().value

        return RelationOperator(relation_type=relation_type, negated=negated, target_field=target_field)

    def _starts_alignment(self) -> bool:
        """Check if the current position begins an alignment arrow.

        An alignment starts with ``ALIGN_LINE`` (for ``=type=>``), or an optional capture label
        prefix ``IDENT ':' ALIGN_LINE``.

        Returns:
            ``True`` if an alignment arrow follows.
        """
        tok = self._current_token
        if tok.type == TokenType.ALIGN_LINE:
            return True
        if tok.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            return self._peek(2).type == TokenType.ALIGN_LINE
        return False

    def _parse_alignment_child(self) -> AlignmentConstraint:
        """``align_child := [IDENT ':'] '=' IDENT? '=>' IDENT '?'? rel_align``

        Parses a single alignment constraint: optional capture name, alignment operator, and
        the target sub-query. The target is a full ``_parse_rel_align`` (right-recursive).

        Returns:
            An ``AlignmentConstraint``.
        """
        capture_name = None
        if self._current_token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            capture_name = self._advance().value
            self._advance()  # consume ':'

        operator = self._parse_alignment_operator(capture_name)
        target = self._parse_rel_align()
        return AlignmentConstraint(operator=operator, target=target)

    def _parse_alignment_operator(self, capture_name: str | None = None) -> AlignmentOperator:
        """``align_op := '=' IDENT? '=>' IDENT '?'?``

        Parses the alignment operator tokens from the lexer decomposition:
        ``ALIGN_LINE [IDENT] ALIGN_ARROW IDENT [QUESTION]``.

        Args:
            capture_name: Optional capture label parsed from the ``name:`` prefix.

        Returns:
            An ``AlignmentOperator``.
        """
        self._expect(TokenType.ALIGN_LINE, "at start of alignment arrow")

        relation_type = None
        if self._current_token.type == TokenType.IDENTIFIER:
            relation_type = self._advance().value

        self._expect(TokenType.ALIGN_ARROW, "in alignment arrow")

        target_field_tok = self._expect(TokenType.IDENTIFIER, "as target field after '=>'")
        target_field = target_field_tok.value

        optional = False
        if self._current_token.type == TokenType.QUESTION:
            optional = True
            self._advance()

        return AlignmentOperator(
            target_field=target_field,
            optional=optional,
            relation_type=relation_type,
            capture_name=capture_name,
        )

    def _parse_sequence_bool(self) -> BCQLNode:
        """``sequence_bool := sequence | sequence_bool ('|' | '&' | '->') sequence``

        Left-associative boolean combination of sequences.  ``&``, ``|``, and ``->`` all share the **same**
        precedence, matching ``Bcql.g4``'s ``booleanQuery`` / ``booleanOperator`` rules. For example,
        ``"a" | "b" & "c"`` parses as ``("a" | "b") & "c"``.

        Symmetric with ``_parse_token_bool`` which does the same thing inside ``[...]``.

        Returns:
            A ``SequenceBoolNode`` when an operator is present, otherwise the inner sequence unchanged.
        """
        left = self._parse_sequence()

        while self._current_token.type in BOOL_OPS:
            op_tok = self._advance()
            operator = BOOL_OPS[op_tok.type]
            right = self._parse_sequence()
            left = SequenceBoolNode(operator=operator, left=left, right=right)

        return left

    def _can_start_capture(self) -> bool:
        """Check if the current token can begin a new ``capture`` production.

        Used by ``_parse_sequence`` to decide whether to collect another element. This set grows as new atom
        alternatives are added in later steps (lookarounds, functions, etc.).

        Includes lookahead to avoid consuming tokens that belong to the ``_parse_rel_align`` level:
        - ``BANG REL_LINE`` is a negated relation arrow, not the start of a negated span.
        - ``IDENT ':' REL_LINE`` or ``IDENT ':' BANG REL_LINE`` is a capture-labelled child relation.
        - ``IDENT ':' ALIGN_LINE`` is a capture-labelled alignment.

        Returns:
            ``True`` if the current token can start an atom.
        """
        tok = self._current_token

        # BANG followed by REL_LINE is a negated relation arrow, handled by _parse_rel_align
        if tok.type == TokenType.BANG:
            return self._peek(1).type != TokenType.REL_LINE

        # IDENT ':' followed by a relation/alignment arrow component is a child relation/alignment label
        if tok.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            after_colon = self._peek(2).type
            if after_colon in (TokenType.REL_LINE, TokenType.ALIGN_LINE):
                return False
            if after_colon == TokenType.BANG and self._peek(3).type == TokenType.REL_LINE:
                return False

        return self._current_token_is_oneof(
            TokenType.LBRACKET,
            TokenType.STRING,
            TokenType.LITERAL_STRING,
            TokenType.UNDERSCORE,
            TokenType.LPAREN,
            TokenType.BANG,
            TokenType.IDENTIFIER,
            TokenType.LT,
            TokenType.LT_SLASH,
            TokenType.ROOT_REL_CARET,
            TokenType.LOOKAHEAD_POS,
            TokenType.LOOKAHEAD_NEG,
            TokenType.LOOKBEHIND_POS,
            TokenType.LOOKBEHIND_NEG,
        )

    def _parse_sequence(self) -> BCQLNode:
        """``sequence := capture | capture sequence``

        Collects adjacent sub-queries by simple juxtaposition, meaning tokens placed
        next to each other without an explicit operator form a sequence
        (e.g. ``"the" "tall" "man"``). When only one element is found, returns it directly.
        Two or more elements produce a ``SequenceNode``.

        See ``token-based.md`` for sequence examples.

        Returns:
            A single child ``BCQLNode`` or a ``SequenceNode``.
        """
        children: list[BCQLNode] = [self._parse_capture()]

        while self._can_start_capture():
            children.append(self._parse_capture())

        if len(children) == 1:
            return children[0]
        return SequenceNode(children=children)

    def _parse_capture(self) -> BCQLNode:
        """``capture := span | IDENT ':' capture``

        Handles named captures like ``A:[word="hello"]``. Multiple labels can be chained
        (e.g. ``A:B:[word="cat"]``) because the rule is right-recursive. This matches
        ``Bcql.g4``'s ``captureQuery: (captureLabel ':')* sequencePartNoCapture``.

        The parser peeks ahead for ``IDENT ':'`` to distinguish a capture label from an
        identifier that starts a function call (step 13) or any other production.

        Returns:
            A ``CaptureNode`` when a label is present, otherwise delegates to ``_parse_span``.
        """
        if self._current_token.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            label_tok = self._advance()
            self._advance()  # consume ':'
            body = self._parse_capture()
            return CaptureNode(label=label_tok.value, body=body)

        return self._parse_span()

    def _parse_span(self) -> BCQLNode:
        """``span := repetition | '!' span | '<' tag ... '>' | '</' tag '>'``

        Handles three span tag forms per ``Bcql.g4``'s ``tag`` rule:
        - Whole span: ``<tag_name attr*/>`` - matches the entire span
        - Start tag: ``<tag_name attr*>`` - matches the start position
        - End tag: ``</tag_name>`` - matches the end position

        The tag name can be an identifier or a quoted string (regex). Attributes follow the
        pattern ``name="value"`` or ``name='value'``.

        Negation (``! span``) wraps repetition per ``Bcql.g4``'s ``sequencePartNoCapture`` rule.

        Returns:
            A ``BCQLNode``: ``SpanQuery`` for tags, ``NegationNode`` for negation, or delegates
            to ``_parse_repetition``.
        """
        # Negation
        if self._current_token.type == TokenType.BANG:
            self._advance()
            operand = self._parse_span()
            return NegationNode(child=operand)

        # End tag: </tag_name>
        if self._current_token.type == TokenType.LT_SLASH:
            self._advance()
            tag_name = self._parse_tag_name()
            self._expect(TokenType.GT, "at end of closing tag")
            return self._apply_node_repetition(SpanQuery(tag_name=tag_name, position="end"))

        # Start or whole tag: <tag_name attr* > or <tag_name attr* />
        if self._current_token.type == TokenType.LT:
            self._advance()
            tag_name = self._parse_tag_name()
            attributes = self._parse_tag_attributes()
            if self._current_token.type == TokenType.SLASH_GT:
                self._advance()
                node = SpanQuery(tag_name=tag_name, position="whole", attributes=attributes)
                return self._apply_node_repetition(node)
            self._expect(TokenType.GT, "at end of opening tag")
            node = SpanQuery(tag_name=tag_name, position="start", attributes=attributes)
            return self._apply_node_repetition(node)

        return self._parse_repetition()

    def _parse_tag_name(self) -> str | StringValue:
        """Parse a tag name: either an ``IDENTIFIER`` or a quoted ``STRING``.

        Returns:
            A plain ``str`` for identifiers, or a ``StringValue`` for quoted strings.
        """
        tok = self._current_token
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return tok.value
        if tok.type in (TokenType.STRING, TokenType.LITERAL_STRING):
            self._advance()
            return StringValue(value=tok.value, is_literal=(tok.type == TokenType.LITERAL_STRING))
        raise self._raise_error(f"Expected tag name, got {display_token(tok)}")

    def _parse_tag_attributes(self) -> dict[str, StringValue]:
        """Parse zero or more tag attributes: ``name="value"``.

        Collects attributes until the current token is ``>`` or ``/>``.

        Returns:
            A dict mapping attribute names to ``StringValue``s.
        """
        attrs: dict[str, StringValue] = {}
        while self._current_token.type == TokenType.IDENTIFIER:
            name_tok = self._advance()
            self._expect(TokenType.EQ, f"after attribute name {name_tok.value!r}")
            value = self._parse_string_value(f"as value for attribute {name_tok.value!r}")
            attrs[name_tok.value] = value
        return attrs

    def _parse_repetition(self) -> BCQLNode:
        """``repetition := atom | repetition quantifier``

        Parses the inner atom first, then greedily consumes any postfix quantifiers (``+``, ``*``, ``?``, ``{n}``,
        ``{n,m}``, ``{n,}``, ``{,m}``). Multiple consecutive quantifiers each wrap the previous result in a new
        ``RepetitionNode``.

        The BNF rule is left-recursive (``repetition quantifier``), which we implement here as an iterative
        while-loop. See ``token-based.md`` for repetition examples.

        Returns:
            The inner atom unchanged when no quantifier follows, or a ``RepetitionNode`` wrapping the atom.
        """
        return self._apply_node_repetition(self._parse_atom())

    def _apply_node_repetition(self, node: BCQLNode) -> BCQLNode:
        """Consume any postfix quantifiers (``+``, ``*``, ``?``, ``{...}``) and wrap *node* in ``RepetitionNode``s.

        Called both by ``_parse_repetition`` (for atoms) and ``_parse_span`` (for tag queries),
        since ``Bcql.g4``'s ``sequencePartNoCapture`` applies ``repetitionAmount*`` to both tags
        and position clauses.

        Args:
            node: The node to which quantifiers are applied.

        Returns:
            The node unchanged when no quantifier follows, or wrapped in ``RepetitionNode``(s).
        """
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

        NOTE: ``{,m}`` (no minimum) is a bcql_py extension not present in ``Bcql.g4``'s ``repetitionAmount`` rule,
        which requires at least one INTEGER before the comma. We accept it as a convenience since it is a common
        regex convention meaning "up to m repetitions".

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
        """``atom := '[' token_expr? ']' | STRING | '_' | '(' global_cst ')' | ...``

        The highest-precedence production in the sequence-level grammar. Handles token queries (``[...]``),
        bare string shorthands (``"man"``), the underscore wildcard (``_``), parenthesized groups,
        root relations, lookarounds, and function calls (``IDENT '(' arg_list ')'``).

        A parenthesized group delegates back up to ``_parse_global_constraint`` (the lowest-precedence level),
        matching ``Bcql.g4``'s ``'(' constrainedQuery ')'`` inside ``sequencePartNoCapture``.

        Returns:
            A ``BCQLNode``.

        Raises:
            BCQLSyntaxError: When the current token cannot start an atom.
        """
        tok = self._current_token

        # Parenthesized group: ( global_cst )
        if tok.type == TokenType.LPAREN:
            self._advance()
            inner = self._parse_global_constraint()
            self._expect(TokenType.RPAREN, "at end of parenthesized group")
            return GroupNode(child=inner)

        # Token query: [constraint]  or  []
        if tok.type == TokenType.LBRACKET:
            return self._parse_token_query()

        # Bare string shorthand: "man" -> TokenQuery(shorthand=StringValue(...))
        if tok.type in (TokenType.STRING, TokenType.LITERAL_STRING):
            return self._parse_string_shorthand()

        #  Underscore wildcard: _
        if tok.type == TokenType.UNDERSCORE:
            self._advance()
            return UnderscoreNode()

        # Root relation: ^-type-> target
        if tok.type == TokenType.ROOT_REL_CARET:
            return self._parse_root_relation()

        # Lookahead / lookbehind assertions
        if tok.type in (TokenType.LOOKAHEAD_POS, TokenType.LOOKAHEAD_NEG):
            return self._parse_lookahead()
        if tok.type in (TokenType.LOOKBEHIND_POS, TokenType.LOOKBEHIND_NEG):
            return self._parse_lookbehind()

        # Function call: IDENT '(' arg_list ')'
        if tok.type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.LPAREN:
            return self._parse_function_call()

        raise self._raise_error(f"Expected a token query, string, '(', or '_', got {display_token(tok)}")

    def _parse_root_relation(self) -> RootRelationNode:
        """``root_rel := '^' '-' IDENT? '->' rel_align``

        Root relations match the root of a dependency tree. The lexer emits
        ``ROOT_REL_CARET REL_LINE [IDENT] REL_ARROW`` for the arrow tokens.
        The capture label, if any, is handled by ``_parse_capture`` which sits above
        ``_parse_atom`` in the precedence chain.

        Returns:
            A ``RootRelationNode``.
        """
        self._expect(TokenType.ROOT_REL_CARET, "at start of root relation")
        self._expect(TokenType.REL_LINE, "in root relation arrow")

        relation_type = None
        if self._current_token.type == TokenType.IDENTIFIER:
            relation_type = self._advance().value

        self._expect(TokenType.REL_ARROW, "in root relation arrow")

        target = self._parse_rel_align()
        return RootRelationNode(relation_type=relation_type, target=target)

    def _parse_lookahead(self) -> LookaheadNode:
        """``lookahead := ('(?=' | '(?!') global_cst ')'``

        The lexer emits a single compound token (``LOOKAHEAD_POS`` or ``LOOKAHEAD_NEG``), then
        the body, then ``RPAREN``. The body is a full ``_parse_global_constraint`` (matching
        G4's ``constrainedQuery`` inside parens).

        Returns:
            A ``LookaheadNode``.
        """
        tok = self._advance()
        positive = tok.type == TokenType.LOOKAHEAD_POS
        body = self._parse_global_constraint()
        self._expect(TokenType.RPAREN, "at end of lookahead assertion")
        return LookaheadNode(positive=positive, body=body)

    def _parse_lookbehind(self) -> LookbehindNode:
        """``lookbehind := ('(?<=' | '(?<!') global_cst ')'``

        Same as ``_parse_lookahead`` but for lookbehind assertions.

        Returns:
            A ``LookbehindNode``.
        """
        tok = self._advance()
        positive = tok.type == TokenType.LOOKBEHIND_POS
        body = self._parse_global_constraint()
        self._expect(TokenType.RPAREN, "at end of lookbehind assertion")
        return LookbehindNode(positive=positive, body=body)

    def _parse_function_call(self) -> FunctionCallNode:
        """``IDENT '(' arg_list ')'`` where ``arg_list := ε | arg (',' arg)*`` and ``arg := global_cst | INT``.

        Parses a built-in function call like ``fcall("query", 3)`` at the sequence level. Arguments can be
        full sub-queries (parsed via ``_parse_global_constraint``) or bare integer d. The parser tries to
        consume an ``INT`` first; if the current token is not an integer, it falls through to parsing a
        full sub-query.

        This matches ``Bcql.g4``'s ``queryFuctionCall`` (sic). G4's ``functionParam``
        allows ``constrainedQuery | constraintValue``, but since a constraintValue string is also a valid
        constrainedQuery, we simplify to ``global_cst | INT``.

        Returns:
            A ``FunctionCallNode``.
        """
        name_tok = self._advance()
        self._expect(TokenType.LPAREN, "after function name")

        args: list[BCQLNode | int] = []
        if self._current_token.type != TokenType.RPAREN:
            args.append(self._parse_function_arg())
            while self._current_token.type == TokenType.COMMA:
                self._advance()
                args.append(self._parse_function_arg())

        self._expect(TokenType.RPAREN, "at end of function call")
        return FunctionCallNode(name=name_tok.value, args=args)

    def _parse_function_arg(self) -> BCQLNode | int:
        """Parse a single function argument: ``arg := global_cst | INT``.

        Bare integers are returned as ``int`` values. Everything else is parsed as a full sub-query
        via ``_parse_global_constraint``.

        Returns:
            An ``int`` for bare integer arguments, or a ``BCQLNode`` for query arguments.
        """
        if self._current_token.type == TokenType.INTEGER and self._peek(1).type in (
            TokenType.COMMA,
            TokenType.RPAREN,
        ):
            return int(self._advance().value)
        return self._parse_global_constraint()

    def _parse_token_query(self) -> TokenQuery:
        """Parse a bracketed token query: ``[`` *token_expr*? ``]``.

        Produces an empty match-all ``TokenQuery(constraint=None)`` for ``[]``, or delegates to
        ``_parse_token_expr`` for the constraint inside brackets.

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

        Per the BCQL spec, a bare string is shorthand for ``[<default_annotation>="..."]``. The parser stores it
        as a ``TokenQuery`` with the ``shorthand`` field set so that the original surface form is preserved during
        round-tripping. See ``token-based.md`` for details on the default annotation convention.

        Returns:
            A ``TokenQuery`` with ``shorthand`` set to a ``StringValue``.
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
        """``token_bool := token_not | token_bool ('|' | '&' | '->') token_not``

        Left-associative boolean combination.  ``&``, ``|``, and ``->`` all share the **same** precedence at every
        grammar level (token constraints, sequence-level, and capture constraints). This matches the
        ``booleanOperator`` rule in ``Bcql.g4``. The ``->`` operator is implication, primarily used in capture
        constraints (e.g. ``A.word = "cat" -> B.word = "dog"``) but allowed at every level by the grammar.

        TODO: ask why `->` is part of "bool" operators since it does not feel like a standard boolean.

        Returns:
            A ``BoolConstraint`` when an operator is present, otherwise the inner constraint unchanged.
        """
        left = self._parse_token_not()

        while self._current_token.type in BOOL_OPS:
            op_tok = self._advance()
            operator = BOOL_OPS[op_tok.type]
            right = self._parse_token_not()
            left = BoolConstraint(operator=operator, left=left, right=right)

        return left

    def _parse_token_not(self) -> ConstraintExpr:
        """``token_not := token_cmp | '!' token_not``

        Prefix negation inside token constraints. Recursively handles chained negations like ``!!expr``
        (though unusual in practice).

        Returns:
            A ``NotConstraint`` when negated, otherwise the inner constraint unchanged.
        """
        if self._current_token.type == TokenType.BANG:
            self._advance()
            operand = self._parse_token_not()
            return NotConstraint(operand=operand)

        return self._parse_token_cmp()

    def _parse_token_cmp(self) -> ConstraintExpr:
        """``token_cmp := IDENT CMP STRING | IDENT '=' 'in' '[' INT ',' INT ']' | IDENT '(' string_list ')' | '(' token_bool ')'``

        Highest-precedence level inside token constraints. Dispatches based on the tokens following the identifier:

        - **Annotation comparison** (``word="man"``, ``pos!="noun"``, ``score>="5"``): Produces an
          ``AnnotationConstraint``. All six comparison operators from ``Bcql.g4``'s ``comparisonOperator`` rule are
          supported: ``=``, ``!=``, ``<``, ``<=``, ``>``, ``>=``.
        - **Integer range** (``pos_confidence=in[50,100]``): Produces an ``IntegerRangeConstraint``.
        - **Function/pseudo-annotation** (``word("man","woman")``): Produces a ``FunctionConstraint``.
          See ``token-based.md`` for details on pseudo-annotation functions (e.g. ``punctAfter``).
        - **Parenthesized sub-expression** (``(word="a" | word="the")``): Recurses into ``_parse_token_bool``.

        Returns:
            A ``ConstraintExpr`` node.

        Raises:
            BCQLSyntaxError: On unexpected tokens inside brackets.
        """
        tok = self._current_token

        # Parenthesized sub-expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_token_bool()
            self._expect(TokenType.RPAREN, "inside token constraint")
            return expr

        # Identifier-led alternatives
        if tok.type != TokenType.IDENTIFIER:
            raise self._raise_error(
                f"Expected annotation name or '(' inside token constraint, got {display_token(tok)}"
            )

        ident_tok = self._advance()
        annotation = ident_tok.value

        # Function call: ident '(' string_list ')'
        if self._current_token.type == TokenType.LPAREN:
            return self._parse_function_constraint(annotation)

        # Comparison: ident CMP_OP ...
        if self._current_token.type in CMP_OPS:
            op_type = self._current_token.type
            op_str = CMP_OPS[op_type]
            self._advance()

            # Integer range: ident '=' 'in' '[' INT ',' INT ']'
            if op_type == TokenType.EQ and self._current_token.type == TokenType.IN:
                return self._parse_integer_range_constraint(annotation)

            return self._parse_annotation_value(annotation, op_str)

        raise self._raise_error(
            f"Expected a comparison operator or '(' after annotation name {annotation!r}, "
            f"got {display_token(self._current_token)}"
        )

    def _parse_annotation_value(self, annotation: str, operator: str) -> AnnotationConstraint:
        """Parse the string value after ``annotation <op>`` where op is any comparison operator.

        Handles both regular strings (``"man"``) and literal strings (``l"e.g."``). See ``token-based.md``
        for discussion of literal strings and regex escaping.

        Args:
            annotation: The annotation name (e.g. ``"word"``).
            operator: One of ``"="``, ``"!="``, ``"<"``, ``"<="``, ``">"``, ``">="``.

        Returns:
            An ``AnnotationConstraint``.

        Raises:
            BCQLSyntaxError: When the value is not a string token.
        """
        tok = self._current_token
        if tok.type not in (TokenType.STRING, TokenType.LITERAL_STRING):
            raise self._raise_error(
                f"Expected a string delimited by single or double quotes after {annotation!r}{operator},"
                f" got {display_token(tok)}"
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
        See ``token-based.md`` for the pseudo-annotation convention where ``[punctAfter=","]`` is syntactic
        sugar for ``[punctAfter(",")]``.

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

    # Capture-constraint grammar (after ::)

    def _parse_cc_bool(
        self,
    ) -> (
        ConstraintComparison
        | ConstraintBoolean
        | ConstraintNot
        | ConstraintLiteral
        | AnnotationRef
        | ConstraintFunctionCall
    ):
        """``cc_bool := cc_not | cc_bool ('&' | '|' | '->') cc_not``

        Left-associative boolean combination of capture constraints. Same precedence rules as
        ``_parse_token_bool``: ``&``, ``|``, and ``->`` all share equal precedence.

        Returns:
            A capture constraint expression node.
        """
        left = self._parse_cc_not()

        while self._current_token.type in BOOL_OPS:
            op_tok = self._advance()
            operator = BOOL_OPS[op_tok.type]
            right = self._parse_cc_not()
            left = ConstraintBoolean(operator=operator, left=left, right=right)

        return left

    def _parse_cc_not(
        self,
    ) -> (
        ConstraintComparison
        | ConstraintNot
        | ConstraintLiteral
        | ConstraintInteger
        | AnnotationRef
        | ConstraintFunctionCall
    ):
        """``cc_not := cc_cmp | '!' cc_not``

        Prefix negation in capture constraints.

        Returns:
            A ``ConstraintNot`` when negated, otherwise delegates to ``_parse_cc_cmp``.
        """
        if self._current_token.type == TokenType.BANG:
            self._advance()
            operand = self._parse_cc_not()
            return ConstraintNot(operand=operand)

        return self._parse_cc_cmp()

    def _parse_cc_cmp(
        self,
    ) -> ConstraintComparison | ConstraintLiteral | ConstraintInteger | AnnotationRef | ConstraintFunctionCall:
        """``cc_cmp := cc_atom | cc_atom CMP cc_atom``

        Comparison level in capture constraints. Handles ``A.word = "over"`` and similar.
        Per ``Bcql.g4``'s ``simpleConstraint`` rule, comparisons chain left-to-right:
        ``a CMP b CMP c`` parses as ``(a CMP b) CMP c``.

        Returns:
            A ``ConstraintComparison`` when a comparison operator is present, otherwise a plain ``cc_atom``.
        """
        left = self._parse_cc_atom()

        while self._current_token.type in CMP_OPS:
            op_tok = self._advance()
            operator = CMP_OPS[op_tok.type]
            right = self._parse_cc_atom()
            left = ConstraintComparison(operator=operator, left=left, right=right)

        return left

    def _parse_cc_atom(self) -> ConstraintLiteral | ConstraintInteger | AnnotationRef | ConstraintFunctionCall:
        """``cc_atom := STRING | INTEGER | IDENT '.' IDENT | IDENT '(' cc_arg_list ')' | '(' cc_bool ')'``

        Highest precedence in the capture constraint grammar. Dispatches based on the current token:

        - **String literal** (``"over"``): produces a ``ConstraintLiteral``.
        - **Integer literal** (``5``): produces a ``ConstraintInteger``.
        - **Identifier followed by ``.``** (``A.word``): produces an ``AnnotationRef``.
        - **Identifier followed by ``(``** (``start(A)``): produces a ``ConstraintFunctionCall``.
        - **Bare identifier** (``A``): produces an ``AnnotationRef`` with no annotation (used as a
          function argument referring to a capture label).
        - **Parenthesized sub-expression**: recurses into ``_parse_cc_bool``.

        Returns:
            A capture constraint atom node.

        Raises:
            BCQLSyntaxError: When the current token cannot start a capture constraint atom.
        """
        tok = self._current_token

        # Parenthesized sub-expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_cc_bool()
            self._expect(TokenType.RPAREN, "in capture constraint")
            return expr

        # String literal
        if tok.type in (TokenType.STRING, TokenType.LITERAL_STRING):
            self._advance()
            return ConstraintLiteral(value=tok.value)

        # Integer literal
        if tok.type == TokenType.INTEGER:
            self._advance()
            return ConstraintInteger(value=int(tok.value))

        # Identifier-led alternatives: A.word, start(...), or bare label
        if tok.type == TokenType.IDENTIFIER:
            ident_tok = self._advance()

            # Annotation reference: IDENT '.' IDENT
            if self._current_token.type == TokenType.DOT:
                self._advance()
                prop_tok = self._expect(TokenType.IDENTIFIER, "after '.' in annotation reference")
                return AnnotationRef(label=ident_tok.value, annotation=prop_tok.value)

            # Function call: IDENT '(' cc_arg_list ')'
            if self._current_token.type == TokenType.LPAREN:
                return self._parse_cc_function_call(ident_tok.value)

            # Bare identifier (capture label used as function argument)
            return AnnotationRef(label=ident_tok.value, annotation="")

        raise self._raise_error(
            f"Expected a string, identifier, integer, or '(' in capture constraint, got {display_token(tok)}"
        )

    def _parse_cc_function_call(self, name: str) -> ConstraintFunctionCall:
        """Parse ``'(' cc_arg_list ')'`` after a function name in a capture constraint.

        Example: ``start(A)`` or ``end(B)``.

        Args:
            name: The function name preceding ``(``.

        Returns:
            A ``ConstraintFunctionCall``.
        """
        self._expect(TokenType.LPAREN, "in capture constraint function call")
        args = []

        if self._current_token.type != TokenType.RPAREN:
            args.append(self._parse_cc_bool())
            while self._current_token.type == TokenType.COMMA:
                self._advance()
                args.append(self._parse_cc_bool())

        self._expect(TokenType.RPAREN, "in capture constraint function call")
        return ConstraintFunctionCall(name=name, args=args)

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
            raise self._raise_error(
                f"Expected a string delimited by single or double quotes {ctx}, got {display_token(tok)}"
            )
        self._advance()
        return StringValue(value=tok.value, is_literal=(tok.type == TokenType.LITERAL_STRING))
