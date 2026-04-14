"""Relations model grammatical dependencies (or other relations) between tokens / spans. The ``-->`` operator connects a source to a target via a named relation type.

The idea here is that we can have one "source" with multiple relation constraints on it, like

_  -nsubj-> _ ;
  !-obj-> "dog"

where there must be a subj relationship but where dog must not be an obj. (It does NOT imply that the word "dog" must be present.)
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode


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
        default=None, description="Relation type (string/regex) or None for any."
    )
    negated: bool = Field(
        default=False, description="True for negated relation (!-type->)."
    )
    target_field: str | None = Field(
        default=None, description="Target field for cross-field relations."
    )

    def to_bcql(self) -> str:
        neg = "!" if self.negated else ""
        rtype = self.relation_type or ""
        field = self.target_field or ""
        return f"{neg}-{rtype}->{field}"


class ChildConstraint(BCQLNode):
    """A single target constraint in a relation query.

    Represents ``-type-> target`` inside a relation expression.
    Multiple child constraints are separated by ``;``. Note that "target" itself can be any BCQL sub-query,
    including another relation query, e.g.
    _ -nsubj-> (_ -amod-> _)

    Attributes:
        operator: The RelationOperator
        target: The target sub-query.
    """

    node_type: Literal["child_constraint"] = "child_constraint"
    operator: RelationOperator = Field(description="The relation operator.")
    target: BCQLNode = Field(description="Target sub-query.")

    def to_bcql(self) -> str:
        return f"{self.operator.to_bcql()} {self.target.to_bcql()}"


class RelationNode(BCQLNode):
    """A dependency relation query: ``source -type-> target [; -type-> target]*``.

    The source is specified once; one or more child constraints follow, separated by ``;``.

    Attributes:
        source: The source of the relation.
        children: One or more target constraints.
    """

    node_type: Literal["relation"] = "relation"
    source: BCQLNode = Field(description="Source of the relation.")
    children: list[ChildConstraint] = Field(
        min_length=1, description="One or more target constraints."
    )

    def to_bcql(self) -> str:
        first = f"{self.source.to_bcql()} {self.children[0].to_bcql()}"
        if len(self.children) == 1:
            return first
        rest = " ; ".join(c.to_bcql() for c in self.children[1:])
        return f"{first} ; {rest}"


class RootRelationNode(BCQLNode):
    """A root relation query: ``^--> target``.

    Root relations are special: they have no source, only a target.
    See https://github.com/instituutnederlandsetaal/BlackLab/blob/dev/site/docs/guide/040_query-language/020_relations.md#root-relations

    Attributes:
        relation_type: Optional relation type filter (usually ``None``
            meaning any root relation).
        target: The target sub-query.
    """

    node_type: Literal["root_relation"] = "root_relation"
    relation_type: str | None = Field(
        default=None, description="Optional relation type filter."
    )
    target: BCQLNode = Field(description="Target sub-query.")

    def to_bcql(self) -> str:
        rtype = self.relation_type or ""
        return f"^-{rtype}-> {self.target.to_bcql()}"
