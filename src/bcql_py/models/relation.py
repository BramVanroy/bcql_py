"""Relations model grammatical dependencies (or other relations) between tokens / spans. The ``-->`` operator connects a source to a target via a named relation type.

The idea here is that we can have one "source" with multiple relation constraints on it, like

_  -nsubj-> _ ;
  !-obj-> "dog"

where there must be a subj relationship but where dog must not be an obj. (It does NOT imply that the word "dog" must be present.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode


if TYPE_CHECKING:
    from bcql_py.models.union import BCQLNodeUnion


__all__ = [
    "RelationOperator",
    "ChildConstraint",
    "RelationNode",
    "RootRelationNode",
]


class RelationOperator(BCQLNode):
    """The operator in a relation query: ``-type->`` or ``!-type->``.
    See https://github.com/instituutnederlandsetaal/BlackLab/blob/dev/site/docs/guide/040_query-language/020_relations.md#negative-child-constraints
    for details on negative relations.

    Attributes:
        relation_type: The relation type as a string or regex pattern (e.g. ``"obj"``, ``"subj|obj"``), or ``None`` for any type.
        negated: ``True`` for ``!-type->``.
        target_field: For cross-field relations (e.g. ``-->corrected``), the target field name.  ``None`` for same-field relations.
    """

    node_type: Literal["relation_operator"] = "relation_operator"
    relation_type: str | None = Field(
        default=None,
        description="Relation type (string/regex) or None for any.",
    )
    negated: bool = Field(
        default=False, description="True for negated relation (!-type->)."
    )
    target_field: str | None = Field(
        default=None, description="Target field for cross-field relations."
    )

    def to_bcql(self) -> str:
        """Return this relation operator in BCQL syntax."""
        neg = "!" if self.negated else ""
        rtype = self.relation_type or ""
        field = self.target_field or ""
        return f"{neg}-{rtype}->{field}"


class ChildConstraint(BCQLNode):
    """A single child constraint in a relation query.

    Represents ``[-label:] -type-> target`` inside a relation expression.
    Multiple child constraints are separated by ``;``. The target itself can be any BCQL sub-query,
    including another relation query (e.g. ``_ -nsubj-> (_ -amod-> _)``).

    Attributes:
        operator: The relation operator (type, negation, target field).
        target: The target sub-query.
        label: Optional capture label on this child relation (e.g. ``rel:-obj-> _``).
    """

    node_type: Literal["child_constraint"] = "child_constraint"
    operator: RelationOperator = Field(description="The relation operator.")
    target: BCQLNodeUnion = Field(description="Target sub-query.")
    label: str | None = Field(
        default=None,
        description="Optional capture label on this child relation.",
    )

    def to_bcql(self) -> str:
        """Return this child constraint in BCQL syntax."""
        prefix = f"{self.label}:" if self.label else ""
        return f"{prefix}{self.operator.to_bcql()} {self.target.to_bcql()}"


class RelationNode(BCQLNode):
    """A dependency relation query: ``source -type-> target [; -type-> target]*``.

    The source is specified once; one or more child constraints follow, separated by ``;``.

    Attributes:
        source: The source of the relation.
        children: One or more target constraints.
    """

    node_type: Literal["relation"] = "relation"
    source: BCQLNodeUnion = Field(description="Source of the relation.")
    children: list[ChildConstraint] = Field(
        min_length=1, description="One or more target constraints."
    )

    def to_bcql(self) -> str:
        """Return this relation query in BCQL syntax."""
        first = f"{self.source.to_bcql()} {self.children[0].to_bcql()}"
        if len(self.children) == 1:
            return first
        rest = " ; ".join(c.to_bcql() for c in self.children[1:])
        return f"{first} ; {rest}"


class RootRelationNode(BCQLNode):
    """A root relation query: ``^-type-> target`` or ``label:^-type-> target``.

    Usually this relation does not have a "type" (since ROOT is the dependency relation from the root),
    but some corpora may differ.

    TODO: see if the Validator and CorpusSpec should account for "allowed root relations"

    Root relations have no source, only a target. They match the root of a dependency tree.

    Attributes:
        relation_type: Optional relation type filter (usually ``None`` meaning any root).
        target: The target sub-query.
        label: Optional capture label.
    """

    node_type: Literal["root_relation"] = "root_relation"
    relation_type: str | None = Field(
        default=None, description="Optional relation type filter."
    )
    target: BCQLNodeUnion = Field(description="Target sub-query.")
    label: str | None = Field(
        default=None, description="Optional capture label."
    )

    def to_bcql(self) -> str:
        """Return this root-relation query in BCQL syntax."""
        prefix = f"{self.label}:" if self.label else ""
        rtype = self.relation_type or ""
        return f"{prefix}^-{rtype}-> {self.target.to_bcql()}"
