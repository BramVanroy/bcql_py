"""Dealing with capturing inside variable assignment, references to it, and constraints inside capture expressions.
This includes the ``label:body`` capture operator, annotation references like ``A.word``, and constraint expressions like ``A.word = "over"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, Union

from pydantic import Field

from bcql_py.models.base import BCQLNode


if TYPE_CHECKING:
    from bcql_py.models.union import BCQLNodeUnion


__all__ = [
    "CaptureNode",
    "AnnotationRef",
    "ConstraintLiteral",
    "ConstraintComparison",
    "ConstraintBoolean",
    "ConstraintNot",
    "ConstraintInteger",
    "ConstraintFunctionCall",
    "CaptureConstraintExpr",
    "GlobalConstraintNode",
]


class CaptureNode(BCQLNode):
    """A capture label applied to a sub-query: ``label:body``, e.g. A:[word="hello"].

    Everything matched by *body* is captured under *label* in the match info.

    Attributes:
        label: The capture group name (e.g. ``"A"``).
        body: The sub-query whose match is captured
    """

    node_type: Literal["capture"] = "capture"
    label: str = Field(description="Capture group name")
    body: BCQLNodeUnion = Field(description="Sub-query to capture.")

    def to_bcql(self) -> str:
        return f"{self.label}:{self.body.to_bcql()}"


class AnnotationRef(BCQLNode):
    """Reference to a captured token's annotation: ``label.annotation``, or a bare capture label.

    Examples:
    - ``A.word`` refers to the ``word`` annotation of capture ``A``.
    - ``A`` as a bare label (typically used as a function argument, e.g. ``start(A)``).

    Attributes:
        label: Capture group name.
        annotation: Annotation name, or empty string for a bare label reference.
    """

    node_type: Literal["annotation_ref"] = "annotation_ref"
    label: str = Field(description="Capture group name")
    annotation: str = Field(
        default="", description="Annotation name, or empty for a bare label."
    )

    def to_bcql(self) -> str:
        if self.annotation:
            return f"{self.label}.{self.annotation}"
        return self.label


class ConstraintLiteral(BCQLNode):
    """A literal string value in a capture constraint.

    Example: the ``"over"`` in ``A.word = "over"``.

    Attributes:
        value: The literal string (without quotes)
        quote_char: The quote character used in the original query, either ``"`` or ``'``.
    """

    node_type: Literal["constraint_literal"] = "constraint_literal"
    value: str = Field(description="Literal string value.")
    quote_char: Literal['"', "'"] = Field(
        default='"', description="Quote character."
    )

    def to_bcql(self) -> str:
        return f"{self.quote_char}{self.value}{self.quote_char}"


class ConstraintComparison(BCQLNode):
    """A comparison in a capture constraint: ``left op right``.

    Supported operators: ``=``, ``!=``, ``<``, ``<=``, ``>``, ``>=``.
    Operators here do not get their own class; should not be needed here.

    Attributes:
        operator: The comparison operator.
        left: Left-hand operand (usually an [AnnotationRef][bcql_py.models.capture.AnnotationRef]).
        right: Right-hand operand (annotation ref, literal, or function call).
    """

    node_type: Literal["constraint_comparison"] = "constraint_comparison"
    operator: Literal["=", "!=", "<", "<=", ">", ">="] = Field(
        description="Comparison operator."
    )
    left: CaptureConstraintExpr = Field(description="Left operand.")
    right: CaptureConstraintExpr = Field(description="Right operand.")

    def to_bcql(self) -> str:
        return f"{self.left.to_bcql()} {self.operator} {self.right.to_bcql()}"


class ConstraintBoolean(BCQLNode):
    """Boolean combination of capture constraints: ``left op right``.

    Operators: ``&`` (AND), ``|`` (OR), ``->`` (implication). All three share the same precedence
    per ``Bcql.g4``'s ``booleanOperator`` rule. The ``->`` implication operator is most commonly
    seen in capture constraints (e.g. ``A.word = "cat" -> B.word = "dog"``) but the grammar
    allows it at every level.

    Attributes:
        operator: ``"&"``, ``"|"``, or ``"->"``.
        left: Left operand.
        right: Right operand.
    """

    node_type: Literal["constraint_boolean"] = "constraint_boolean"
    operator: Literal["&", "|", "->"] = Field(description="Boolean operator")
    left: CaptureConstraintExpr = Field(description="Left operand.")
    right: CaptureConstraintExpr = Field(description="Right operand.")

    def to_bcql(self) -> str:
        return f"{self.left.to_bcql()} {self.operator} {self.right.to_bcql()}"


class ConstraintNot(BCQLNode):
    """Logical NOT in a capture constraint

    Attributes:
        operand: The constraint being negated.
    """

    node_type: Literal["constraint_not"] = "constraint_not"
    operand: CaptureConstraintExpr = Field(description="Constraint to negate.")

    def to_bcql(self) -> str:
        return f"!{self.operand.to_bcql()}"


class ConstraintInteger(BCQLNode):
    """An integer literal in a capture constraint.

    Example: the ``5`` in ``focus.pos > 5``.

    Attributes:
        value: The integer value.
    """

    node_type: Literal["constraint_integer"] = "constraint_integer"
    value: int = Field(description="Integer value.")

    def to_bcql(self) -> str:
        return str(self.value)


class ConstraintFunctionCall(BCQLNode):
    """A function call in a capture constraint.

    Examples: ``start(A)`` or ``end(B)`` used in expressions like
    ``start(B) < start(A)``.

    Attributes:
        name: Function name (e.g. ``"start"``, ``"end"``).
        args: Function arguments (annotation refs, literals, etc.).
    """

    node_type: Literal["constraint_function_call"] = "constraint_function_call"
    name: str = Field(description="Function name.")
    args: list[CaptureConstraintExpr] = Field(
        description="Function arguments."
    )

    def to_bcql(self) -> str:
        args_str = ", ".join(a.to_bcql() for a in self.args)
        return f"{self.name}({args_str})"


# Discriminated union for capture constraint expressions
CaptureConstraintExpr = Annotated[
    Union[
        AnnotationRef,
        ConstraintLiteral,
        ConstraintInteger,
        ConstraintComparison,
        ConstraintBoolean,
        ConstraintNot,
        ConstraintFunctionCall,
    ],
    Field(discriminator="node_type"),
]

ConstraintComparison.model_rebuild()
ConstraintBoolean.model_rebuild()
ConstraintNot.model_rebuild()
ConstraintFunctionCall.model_rebuild()


class GlobalConstraintNode(BCQLNode):
    """A query with a global capture constraint.

    The constraint expression follows the ``::`` operator and relates captures defined in *body*.

    Example: ``A:[] "by" B:[] :: A.word = B.word`` where `A:[] "by" B:[]` is the body and `A.word = B.word` is the constraint expression.

    Attributes:
        body: The main query containing captures.
        constraint: The constraint expression relating captures.
    """

    node_type: Literal["global_constraint"] = "global_constraint"
    body: BCQLNodeUnion = Field(description="Main query containing captures.")
    constraint: CaptureConstraintExpr = Field(
        description="Constraint expression."
    )

    def to_bcql(self) -> str:
        return f"{self.body.to_bcql()} :: {self.constraint.to_bcql()}"
