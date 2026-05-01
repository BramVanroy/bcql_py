"""AST nodes for sequence-level constructions.

These models represent sequences of tokens, repetition quantifiers,
parenthesized groups, logical union/intersection/negation at the
sequence level, and the ``_`` underscore used in relation queries where applicable
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode


if TYPE_CHECKING:
    # Imported only for static type-checking. At runtime the annotations are
    # strings (``from __future__ import annotations``); the real union is
    # resolved by ``model_rebuild`` from inside [models/union.py](union.py).
    from bcql_py.models.union import BCQLNodeUnion


__all__ = [
    "SequenceNode",
    "RepetitionNode",
    "GroupNode",
    "SequenceBoolNode",
    "NegationNode",
    "UnderscoreNode",
]


class SequenceNode(BCQLNode):
    """An ordered sequence of adjacent tokens / sub-queries.
    A very high-level node type that can represent an entire query or a sub-sequence

    Attributes:
        children: The ordered list of child nodes in the sequence.
    """

    node_type: Literal["sequence"] = "sequence"
    children: list[BCQLNodeUnion] = Field(
        min_length=2, description="Ordered child nodes."
    )

    def to_bcql(self) -> str:
        """Return this sequence in BCQL syntax."""
        return " ".join(child.to_bcql() for child in self.children)


class RepetitionNode(BCQLNode):
    """A repetition quantifier applied to a sub-query.

    Supports ``+`` (1+), ``*`` (0+), ``?`` (0 or 1), ``{n}``, ``{n,m}``,
    ``{n,}``. Note that "up to" quantifiers like ``{0,m}`` are exported as
    ``{,m}`` and may therefore be different in surface form from the original.

    Attributes:
        child: The sub-query being repeated.
        min_count: Minimum number of repetitions (inclusive, min. 0).
        max_count: Maximum number of repetitions (inclusive), or ``None``
            for unlimited.
    """

    node_type: Literal["repetition"] = "repetition"
    child: BCQLNodeUnion = Field(description="The sub-query to repeat")
    min_count: int = Field(ge=0, description="Minimum repetitions (inclusive)")
    max_count: int | None = Field(
        default=None,
        description="Maximum repetitions (inclusive), or None for unlimited.",
    )

    @property
    def quantifier(self) -> str:
        """Return the BCQL quantifier string for this repetition."""
        if self.min_count == 0 and self.max_count is None:
            return "*"
        if self.min_count == 1 and self.max_count is None:
            return "+"
        if self.min_count == 0 and self.max_count == 1:
            return "?"
        if self.max_count is None:
            return f"{{{self.min_count},}}"
        if self.min_count == self.max_count:
            return f"{{{self.min_count}}}"
        if not self.min_count:
            return f"{{,{self.max_count}}}"
        return f"{{{self.min_count},{self.max_count}}}"

    def to_bcql(self) -> str:
        """Return this repetition expression in BCQL syntax."""
        return f"{self.child.to_bcql()}{self.quantifier}"


class GroupNode(BCQLNode):
    """A parenthesized group of sub-queries.

    Groups allow applying repetition operators or capture constraints to
    a complex sub-expression. We specify that there can only be one child node in a group,
    which typically would be a SequenceNode if there are multiple adjacent tokens or
    a token-level Node.

    Attributes:
        child: The inner sub-query.
    """

    node_type: Literal["group"] = "group"
    child: BCQLNodeUnion = Field(description="The inner sub-query")

    def to_bcql(self) -> str:
        """Return this parenthesized group in BCQL syntax."""
        return f"({self.child.to_bcql()})"


class SequenceBoolNode(BCQLNode):
    """Sequence-level boolean combination (``&``, ``|``, ``->``).

    Binary, left-associative node mirroring the ``booleanOperator`` rule in ``Bcql.g4``:
    all three operators share the same precedence. For example, ``"a" | "b" & "c"``
    parses as ``("a" | "b") & "c"``.

    Attributes:
        operator: The boolean operator.
        left: The left operand.
        right: The right operand.
    """

    node_type: Literal["sequence_bool"] = "sequence_bool"
    operator: Literal["&", "|", "->"] = Field(description="Boolean operator.")
    left: BCQLNodeUnion = Field(description="Left operand.")
    right: BCQLNodeUnion = Field(description="Right operand.")

    def to_bcql(self) -> str:
        """Return this sequence-level boolean expression in BCQL syntax."""
        return f"{self.left.to_bcql()} {self.operator} {self.right.to_bcql()}"


class NegationNode(BCQLNode):
    """Sequence-level negation (``!``).

    Negation sits at the span level in the precedence chain (above repetition), so
    ``!"man"+`` parses as ``!("man"+)`` per ``Bcql.g4``'s ``sequencePartNoCapture`` rule.
    The child is always a single span-level node (never a bare sequence), so
    ``to_bcql`` just prepends ``!`` without extra parentheses.

    Attributes:
        child: The sub-query being negated.
    """

    node_type: Literal["negation"] = "negation"
    child: BCQLNodeUnion = Field(description="The sub-query to negate.")

    def to_bcql(self) -> str:
        """Return this negated sub-query in BCQL syntax."""
        return f"!{self.child.to_bcql()}"


class UnderscoreNode(BCQLNode):
    """The ``_`` wildcard used in relation queries.

    Distinct from ``[]`` (match-all token): ``_`` means "any source or
    target" in a relation expression without constraining token count.
    """

    node_type: Literal["underscore"] = "underscore"

    def to_bcql(self) -> str:
        """Return the underscore wildcard in BCQL syntax."""
        return "_"
