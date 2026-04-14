"""Token-level annotations"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from bcql_py.models.base import BCQLNode


class StringValue(BCQLNode):
    """A quoted string value inside a BCQL query.

    Handles regular strings, literal strings (prefixed with ``l``), and
    sensitivity flags (``(?-i)`` for sensitive, ``(?i)`` for insensitive).

    Attributes:
        value: The raw string content (without surrounding quotes).
        is_literal: ``True`` when prefixed with ``l`` (e.g. ``l"e.g."``).
        sensitivity: ``"default"`` follows the default value (unspecified),
         ``"sensitive"`` for ``(?-i)``, ``"insensitive"``
            for ``(?i)``.

    Example::

        >>> StringValue(value="(?-i)Panama").to_bcql()
        '"(?-i)Panama"'
    """

    node_type: Literal["string_value"] = "string_value"
    value: str = Field(description="Raw string content (without surrounding quotes).")
    is_literal: bool = Field(default=False, description="True if prefixed with 'l' (literal string).")
    sensitivity: Literal["default", "sensitive", "insensitive"] = Field(
        default="default",
        description="Matching sensitivity: 'default', 'sensitive' ((?-i)), or 'insensitive' ((?i)).",
    )
    quote_char: Literal['"', "'"] = Field(
        default='"',
        description="The quote character used in the original query.",
    )

    def to_bcql(self) -> str:
        qchar = self.quote_char
        prefix = "l" if self.is_literal else ""
        return f"{prefix}{qchar}{self.value}{qchar}"


class AnnotationConstraint(BCQLNode):
    """A single annotation comparison: ``annotation op "value"``.
    Typically between an identifier, an operator, and a string value.
    Note that the identifier is not semantically specified here! It fully depends
    on the corpus which attributes (like word, lemma, pos) are available. So here
    ``annotation`` is underspecified as just a string.

    Example: ``word="man"`` or ``pos != "noun"``.

    Attributes:
        annotation: The annotation name (e.g. ``"word"``, ``"lemma"``).
        operator: ``"="`` or ``"!="``.
        value: The value being compared against.
    """

    node_type: Literal["annotation_constraint"] = "annotation_constraint"
    annotation: str = Field(description="Annotation name (e.g. 'word', 'lemma', 'pos').")
    operator: Literal["=", "!=", "<", "<=", ">", ">="] = Field(description="Comparison operator.")
    value: StringValue = Field(description="The value being compared against.")

    def to_bcql(self) -> str:
        return f"{self.annotation}{self.operator}{self.value.to_bcql()}"


class IntegerRangeConstraint(BCQLNode):
    """An integer range constraint, such as a parser's confidence: ``annotation=in[min,max]``.

    Example: ``pos_confidence=in[50,100]``.

    Note that we require both min and max vals to be given. No implicit "infinite" or "zero" bounds.

    Attributes:
        annotation: The annotation name.
        min_val: Inclusive lower bound.
        max_val: Inclusive upper bound.
    """

    node_type: Literal["integer_range_constraint"] = "integer_range_constraint"
    annotation: str = Field(description="Annotation name.")
    min_val: int = Field(description="Inclusive lower bound.")
    max_val: int = Field(description="Inclusive upper bound.")

    def to_bcql(self) -> str:
        return f"{self.annotation}=in[{self.min_val},{self.max_val}]"


class FunctionConstraint(BCQLNode):
    """A function-call constraint inside token brackets.

    TODO: check for predefined functions in blacklab?

    Attributes:
        name: The function / pseudo-annotation name.
        args: The string arguments to the function.
    """

    node_type: Literal["function_constraint"] = "function_constraint"
    name: str = Field(description="Function / pseudo-annotation name.")
    args: list[StringValue] = Field(description="String arguments.")

    def to_bcql(self) -> str:
        args_str = ", ".join(a.to_bcql() for a in self.args)
        return f"{self.name}({args_str})"


class NotConstraint(BCQLNode):
    """Logical NOT on a token-level constraint: ``!expr``.

    Typically for a capture group: ``!(pos="noun" | pos="verb")``.

    Attributes:
        operand: The constraint being negated.
    """

    node_type: Literal["not_constraint"] = "not_constraint"
    operand: ConstraintExpr = Field(description="The constraint to negate.")

    def to_bcql(self) -> str:
        inner = self.operand.to_bcql()
        # Wrap compound expressions in parens for clarity
        if isinstance(self.operand, BoolConstraint):
            return f"!({inner})"
        return f"!{inner}"


class BoolConstraint(BCQLNode):
    """Boolean combination of token-level constraints: ``left op right``.

    The operator is ``&`` (AND), ``|`` (OR), or ``->`` (implication).  Per the BCQL spec / ``Bcql.g4``,
    all three share **identical** precedence and are left-associative. See the ``booleanOperator`` rule
    in ``Bcql.g4``. Naming-wise calling it "boolean" might be somewhat confusing for the implication case though

    Not to be confused with sequence-level boolean operators (also ``&`` and ``|``) which
    combine whole sub-queries instead of token constraints. See sequence.UnionNode and sequence.IntersectionNode for those.

    Attributes:
        operator: ``"&"``, ``"|"``, or ``"->"``.
        left: Left operand.
        right: Right operand.
    """

    node_type: Literal["bool_constraint"] = "bool_constraint"
    operator: Literal["&", "|", "->"] = Field(description="Boolean operator: '&', '|', or '->'.")
    left: ConstraintExpr = Field(description="Left operand.")
    right: ConstraintExpr = Field(description="Right operand.")

    def to_bcql(self) -> str:
        return f"{self.left.to_bcql()} {self.operator} {self.right.to_bcql()}"


# Discriminated union type for token-level constraint expressions
ConstraintExpr = Annotated[
    Union[
        AnnotationConstraint,
        IntegerRangeConstraint,
        FunctionConstraint,
        NotConstraint,
        BoolConstraint,
    ],
    Field(discriminator="node_type"),
]

# Rebuild models that reference the forward-ref union to ensure the discriminated union works correctly
# If we don't do this, we'll get a Pydantic error about the forward reference not being resolved when
# we try to create a NotConstraint or BoolConstraint
NotConstraint.model_rebuild()
BoolConstraint.model_rebuild()


class TokenQuery(BCQLNode):
    """A single token query: ``[...]``, ``"string"`` shorthand, or ``[]``.

    Attributes:
        constraint: The constraint expression inside the brackets, or
            ``None`` for match-all (``[]``).
        negated: ``True`` for the negated form ``![...]``.
        shorthand: When the query was written as a bare string like
            ``"man"`` (shorthand for ``[word="man"]``), this stores
            the StringValue].  If set, ``constraint`` is ``None``.
    """

    node_type: Literal["token_query"] = "token_query"
    constraint: ConstraintExpr | None = Field(
        default=None,
        description="Constraint inside brackets, or None for match-all",
    )
    negated: bool = Field(default=False, description="True for ![...].")
    shorthand: StringValue | None = Field(
        default=None,
        description='Bare string shorthand (e.g. \'"man"\' for [word="man"])',
    )

    def to_bcql(self) -> str:
        if self.shorthand is not None:
            prefix = "!" if self.negated else ""
            return f"{prefix}{self.shorthand.to_bcql()}"
        prefix = "!" if self.negated else ""
        if self.constraint is None:
            return f"{prefix}[]"
        return f"{prefix}[{self.constraint.to_bcql()}]"
