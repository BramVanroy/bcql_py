"""Alignment queries use the ``==>`` operator to find cross-field alignments
between versions of a parallel corpus (e.g. English -> Dutch).

Similar to models/relation but with different operators and semantics.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode


__all__ = ["AlignmentOperator", "AlignmentConstraint", "AlignmentNode"]


class AlignmentOperator(BCQLNode):
    """The operator in an alignment query: ``=type=>field`` or ``==>field?``.

    See https://github.com/instituutnederlandsetaal/BlackLab/blob/dev/site/docs/guide/040_query-language/030_parallel.md

    Attributes:
        target_field: The target field name (e.g. ``"nl"``).
        optional: ``True`` when alignment is optional (``==>nl?``).
        relation_type: Optional type filter (e.g. ``"word"`` in ``=word=>nl``).  ``None`` means any alignment relation
        capture_name: Override for the capture group name (default ``"rels"``). Set by ``name:==>field`` syntax
    """

    node_type: Literal["alignment_operator"] = "alignment_operator"
    target_field: str = Field(description="Target field name.")
    optional: bool = Field(
        default=False, description="True for optional alignment (==>field?)."
    )
    relation_type: str | None = Field(
        default=None, description="Relation type filter."
    )
    capture_name: str | None = Field(
        default=None, description="Override capture group name."
    )

    def to_bcql(self) -> str:
        rtype = self.relation_type or ""
        opt = "?" if self.optional else ""
        capture = f"{self.capture_name}:" if self.capture_name else ""
        return f"{capture}={rtype}=>{self.target_field}{opt}"


class AlignmentConstraint(BCQLNode):
    """One alignment constraint: ``operator target``

    Multiple alignment constraints are separated by ``;``.

    Attributes:
        operator: The [AlignmentOperator][bcql_py.models.alignment.AlignmentOperator].
        target: The target sub-query.
    """

    node_type: Literal["alignment_constraint"] = "alignment_constraint"
    operator: AlignmentOperator = Field(description="Alignment operator.")
    target: BCQLNode = Field(description="Target sub-query.")

    def to_bcql(self) -> str:
        return f"{self.operator.to_bcql()} {self.target.to_bcql()}"


class AlignmentNode(BCQLNode):
    """A parallel alignment query: ``source ==>field target [; ==>field target]*``.
    Attributes:
        source: The source query in the primary field
        alignments: One or more alignment constraints.
    """

    node_type: Literal["alignment"] = "alignment"
    source: BCQLNode = Field(description="Source query in primary field.")
    alignments: list[AlignmentConstraint] = Field(
        min_length=1, description="Alignment constraint(s)"
    )

    def to_bcql(self) -> str:
        first = f"{self.source.to_bcql()} {self.alignments[0].to_bcql()}"
        if len(self.alignments) == 1:
            return first
        rest = " ; ".join(a.to_bcql() for a in self.alignments[1:])
        return f"{first} ; {rest}"
