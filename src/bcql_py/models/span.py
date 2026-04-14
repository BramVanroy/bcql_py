"""XML span models"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode
from bcql_py.models.token import StringValue


class SpanQuery(BCQLNode):
    """A span (XML tag) query.

    Attributes:
        tag_name: The tag name as a plain string, (or StringValue for regex)
            when the name is a regex (e.g. ``<"person|location"/>``).
        position: ``"whole"`` for ``<s/>``, ``"start"`` for ``<s>``,
            ``"end"`` for ``</s>``.
        attributes: XML attributes expressed as ``name=value`` pairs.
            Values are plain strings (regex allowed inside them).
    """

    node_type: Literal["span_query"] = "span_query"
    tag_name: str | StringValue = Field(description="Tag name (plain string or StringValue for regex")
    position: Literal["whole", "start", "end"] = Field(description="Which part of the span to match")
    attributes: dict[str, str] = Field(default_factory=dict, description="XML attributes as name:value pairs")

    @property
    def tag_str(self) -> str:
        if isinstance(self.tag_name, StringValue):
            return self.tag_name.to_bcql()
        return self.tag_name

    @property
    def attrs_str(self) -> str:
        if not self.attributes:
            return ""
        parts = [f' {k}="{v}"' for k, v in self.attributes.items()]
        return "".join(parts)

    def to_bcql(self) -> str:
        tag = self.tag_str()
        attrs = self.attrs_str()
        if self.position == "whole":
            return f"<{tag}{attrs}/>"
        elif self.position == "start":
            return f"<{tag}{attrs}>"
        else:
            return f"</{tag}>"


class PositionFilterNode(BCQLNode):
    """A position-filter operator: ``within``, ``containing``, or ``overlap``.

    Exampl``"baker" within <person/>`` means: find ``"baker"`` that occurs
    inside a ``<person/>`` span.

    These operators are **right-associative**, so ``A within B within C`` is parsed as ``A within (B within C)``.

    Attributes:
        operator: One of ``"within"``, ``"containing"``, ``"overlap"``.
        left: The query whose hits are filtered.
        right: The span/query that defines the positional constraint.
    """

    node_type: Literal["position_filter"] = "position_filter"
    operator: Literal["within", "containing", "overlap"] = Field(
        description="Position filter operator.",
    )
    left: BCQLNode = Field(description="The query to filter.")
    right: BCQLNode = Field(description="The positional constraint.")

    def to_bcql(self) -> str:
        return f"{self.left.to_bcql()} {self.operator} {self.right.to_bcql()}"
