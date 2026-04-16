"""XML span models"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode
from bcql_py.models.token import StringValue


class SpanQuery(BCQLNode):
    """A span (XML tag) query.

    Three forms exist per ``Bcql.g4``'s ``tag`` rule:
    - Whole span: ``<s/>`` or ``<ne type="PERS"/>``
    - Start tag: ``<s>``
    - End tag: ``</s>``

    The tag name can be a plain identifier (``s``, ``ne``) or a quoted string
    for regex patterns (``<"person|location"/>``).

    Attributes:
        tag_name: The tag name as a plain string or ``StringValue`` for regex.
        position: ``"whole"`` for ``<s/>``, ``"start"`` for ``<s>``, ``"end"`` for ``</s>``.
        attributes: XML attributes as ``name: StringValue`` pairs (e.g. ``type="PERS"``).
    """

    node_type: Literal["span_query"] = "span_query"
    tag_name: str | StringValue = Field(description="Tag name (plain string or StringValue for regex).")
    position: Literal["whole", "start", "end"] = Field(description="Which part of the span to match.")
    attributes: dict[str, StringValue] = Field(
        default_factory=dict, description="XML attributes as name: StringValue pairs."
    )

    @property
    def tag_str(self) -> str:
        if isinstance(self.tag_name, StringValue):
            return self.tag_name.to_bcql()
        return self.tag_name

    @property
    def attrs_str(self) -> str:
        if not self.attributes:
            return ""
        return "".join(f" {k}={v.to_bcql()}" for k, v in self.attributes.items())

    def to_bcql(self) -> str:
        tag = self.tag_str
        attrs = self.attrs_str
        if self.position == "whole":
            return f"<{tag}{attrs}/>"
        if self.position == "start":
            return f"<{tag}{attrs}>"
        return f"</{tag}>"


class PositionFilterNode(BCQLNode):
    """A position-filter operator: ``within``, ``containing``, or ``overlap``.

    Example: ``"baker" within <person/>`` means find ``"baker"`` inside a ``<person/>`` span.

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
