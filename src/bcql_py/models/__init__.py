"""Public AST model exports for bcql_py.models."""

from bcql_py.models.alignment import (
    AlignmentConstraint,
    AlignmentNode,
    AlignmentOperator,
)
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
    FunctionConstraint,
    IntegerRangeConstraint,
    NotConstraint,
    StringValue,
    TokenQuery,
)

# Importing ``union`` here is load-bearing: it builds the discriminated
# ``BCQLNodeUnion`` type and rebuilds every model that references it as a
# forward annotation. Without this import, fields typed as ``BCQLNodeUnion``
# would fail to resolve at validation time. See [union.py](union.py).
from bcql_py.models.union import BCQLNodeUnion


__all__ = [
    # base
    "BCQLNode",
    "BCQLNodeUnion",
    # token
    "StringValue",
    "AnnotationConstraint",
    "IntegerRangeConstraint",
    "FunctionConstraint",
    "NotConstraint",
    "BoolConstraint",
    "TokenQuery",
    # sequence
    "SequenceNode",
    "RepetitionNode",
    "GroupNode",
    "SequenceBoolNode",
    "NegationNode",
    "UnderscoreNode",
    # lookaround
    "LookaheadNode",
    "LookbehindNode",
    # span
    "SpanQuery",
    "PositionFilterNode",
    # capture
    "CaptureNode",
    "GlobalConstraintNode",
    "AnnotationRef",
    "ConstraintLiteral",
    "ConstraintInteger",
    "ConstraintComparison",
    "ConstraintBoolean",
    "ConstraintNot",
    "ConstraintFunctionCall",
    # relation
    "RelationOperator",
    "ChildConstraint",
    "RelationNode",
    "RootRelationNode",
    # alignment
    "AlignmentOperator",
    "AlignmentConstraint",
    "AlignmentNode",
    # function
    "FunctionCallNode",
]
