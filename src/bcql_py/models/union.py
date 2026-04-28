"""Discriminated union over every concrete BCQL AST node.

Why a discriminated union?

Pydantic v2 serializes (and validates) model fields based on the *declared*
type of the field, NOT the runtime type of the instance. That means it will
see that some fields like "children" is annotated as "list[BCQLNode]".
But since the base class ``BCQLNode`` has no fields, Pydantic emits an empty
JSON object ``{}`` for every node, losing all the useful information in the tree.

A *discriminated* (aka *tagged*) union solves both directions during runtime:

- On serialization, Pydantic walks the union, picks the variant that
  matches the instance's runtime type, and emits all of that variant's
  fields, recursively. Output is now a faithful, fully nested JSON tree.
- On deserialization, Pydantic reads the ``node_type`` field of the
  incoming data, looks it up in the discriminator map, and validates
  against that subclass directly. This is much faster than trying every
  union variant in turn ("smart union"), and unambiguous when several
  variants share field names (e.g. ``left`` / ``right`` on the various
  boolean nodes).

The discriminator key is ``node_type``: every concrete subclass declares a
unique ``node_type: Literal["..."]``. That is what makes the union
*discriminated*: Pydantic does not need to guess; it can just read the node_type.

How the forward-reference works:

Field annotations across the model modules refer to ``BCQLNodeUnion`` by
name (e.g. ``child: BCQLNodeUnion``). With ``from __future__ import
annotations`` enabled, those annotations are stored as strings and resolved
lazily, which lets us declare each model before the union itself exists.

This module imports every concrete subclass, builds the union, and then
calls ``model_rebuild`` on each affected model with our local namespace so
Pydantic can finally resolve the ``"BCQLNodeUnion"`` strings to the real
type in runtime.

Importing this module is what activates the discriminated dispatch, so
[models/__init__.py](__init__.py) imports it eagerly. Any code path that
reaches the model package therefore gets correctly-rebuilt models.
"""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from bcql_py.models.alignment import (
    AlignmentConstraint,
    AlignmentNode,
    AlignmentOperator,
)
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


__all__ = ["BCQLNodeUnion"]


BCQLNodeUnion = Annotated[
    Union[
        # token-level
        StringValue,
        AnnotationConstraint,
        IntegerRangeConstraint,
        FunctionConstraint,
        NotConstraint,
        BoolConstraint,
        TokenQuery,
        # sequence-level
        SequenceNode,
        RepetitionNode,
        GroupNode,
        SequenceBoolNode,
        NegationNode,
        UnderscoreNode,
        # lookaround
        LookaheadNode,
        LookbehindNode,
        # span
        SpanQuery,
        PositionFilterNode,
        # capture and capture constraints
        CaptureNode,
        AnnotationRef,
        ConstraintLiteral,
        ConstraintInteger,
        ConstraintComparison,
        ConstraintBoolean,
        ConstraintNot,
        ConstraintFunctionCall,
        GlobalConstraintNode,
        # relations
        RelationOperator,
        ChildConstraint,
        RelationNode,
        RootRelationNode,
        # alignment / parallel
        AlignmentOperator,
        AlignmentConstraint,
        AlignmentNode,
        # functions
        FunctionCallNode,
    ],
    Field(discriminator="node_type"),
]
"""Annotated union of every concrete BCQL AST node, discriminated by ``node_type``.

Use this anywhere a field can hold *any* BCQL node (sub-queries, sequence
children, relation targets, etc.). For fields restricted to a smaller subset
of node types, prefer the narrower unions defined alongside their owners
(e.g. ``ConstraintExpr`` in [token.py](token.py) for token-level constraints,
``CaptureConstraintExpr`` in [capture.py](capture.py) for capture constraints).
Narrower unions give better validation errors and make the schema honest about
which nodes are actually legal in that position.
"""


# ``model_rebuild`` re-resolves the field annotations against the namespace we
# pass in, swapping each ``"BCQLNodeUnion"`` forward-ref string for the real
# union type. Only models that *contain* a ``BCQLNodeUnion`` annotation need
# rebuilding; leaf models (``StringValue``, ``UnderscoreNode``, ...) have no
# such fields.
_namespace: dict[str, object] = {"BCQLNodeUnion": BCQLNodeUnion}

for _model in (
    SequenceNode,
    RepetitionNode,
    GroupNode,
    SequenceBoolNode,
    NegationNode,
    LookaheadNode,
    LookbehindNode,
    PositionFilterNode,
    CaptureNode,
    GlobalConstraintNode,
    ChildConstraint,
    RelationNode,
    RootRelationNode,
    AlignmentConstraint,
    AlignmentNode,
    FunctionCallNode,
):
    _model.model_rebuild(_types_namespace=_namespace)
