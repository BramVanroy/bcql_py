"""Dealing with capturing inside variable assignment, references to it, and constraints inside capture expressions.
This includes the ``label:body`` capture operator, annotation references like ``A.word``, and constraint expressions like ``A.word = "over"``.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from bcql_py.models.base import BCQLNode


class CaptureNode(BCQLNode):
    """A capture label applied to a sub-query: ``label:body``, e.g. A:[word="hello"].

    Everything matched by *body* is captured under *label* in the match info.

    Attributes:
        label: The capture group name (e.g. ``"A"``).
        body: The sub-query whose match is captured
    """

    node_type: Literal["capture"] = "capture"
    label: str = Field(description="Capture group name")
    body: BCQLNode = Field(description="Sub-query to capture.")

    def to_bcql(self) -> str:
        return f"{self.label}:{self.body.to_bcql()}"


class AnnotationRef(BCQLNode):
    """Reference to a captured token's annotation: ``label.annotation``.

    Example: ``A.word`` refers to the ``word`` annotation of capture ``A``.

    Attributes:
        label: Capture group name.
        annotation: Annotation name.
    """

    node_type: Literal["annotation_ref"] = "annotation_ref"
    label: str = Field(description="Capture group name")
    annotation: str = Field(description="Annotation name.")

    def to_bcql(self) -> str:
        return f"{self.label}.{self.annotation}"


class ConstraintLiteral(BCQLNode):
    """A literal string value in a capture constraint.

    Example: the ``"over"`` in ``A.word = "over"``.

    Attributes:
        value: The literal string (without quotes)
        quote_char: The quote character used in the original query, either ``"`` or ``'``.
    """

    node_type: Literal["constraint_literal"] = "constraint_literal"
    value: str = Field(description="Literal string value.")
    quote_char: Literal['"', "'"] = Field(default='"', description="Quote character.")

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
    operator: Literal["=", "!=", "<", "<=", ">", ">="] = Field(description="Comparison operator.")
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
    args: list[CaptureConstraintExpr] = Field(description="Function arguments.")

    def to_bcql(self) -> str:
        args_str = ", ".join(a.to_bcql() for a in self.args)
        return f"{self.name}({args_str})"


# Discriminated union for capture constraint expressions
CaptureConstraintExpr = Annotated[
    Union[
        AnnotationRef,
        ConstraintLiteral,
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
    body: BCQLNode = Field(description="Main query containing captures.")
    constraint: CaptureConstraintExpr = Field(description="Constraint expression.")

    def to_bcql(self) -> str:
        return f"{self.body.to_bcql()} :: {self.constraint.to_bcql()}"
