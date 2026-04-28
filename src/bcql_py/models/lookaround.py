"""Regex-based lookahead and lookbehind assertions require special handling.
Note that these occur outside of string literals but are lookarounds on Node values.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode


__all__ = ["LookaheadNode", "LookbehindNode"]


class LookaheadNode(BCQLNode):
    """A lookahead assertion: ``(?=...)`` (positive) or ``(?!...)`` (negative).

    Matches a position only if the enclosed query matches (or doesn't match) the tokens that follow.

    Attributes:
        positive: ``True`` for ``(?= ...)``, ``False`` for ``(?! ...)``.
        body: The sub-query that must (or must not) match ahead.
    """

    node_type: Literal["lookahead"] = "lookahead"
    positive: bool = Field(
        description="True for positive (?=), False for negative (?!)."
    )
    body: BCQLNode = Field(description="The sub-query to match ahead.")

    def to_bcql(self) -> str:
        op = "?=" if self.positive else "?!"
        return f"({op} {self.body.to_bcql()})"


class LookbehindNode(BCQLNode):
    """A lookbehind assertion: ``(?<=...)`` (positive) or ``(?<!...)`` (negative).

    Matches a position only if the enclosed query matches (or doesn't match) the tokens that precede

    Attributes:
        positive: ``True`` for ``(?<=...)``, ``False`` for ``(?<!...)``.
        body: The sub-query that must (or must not) match behind
    """

    node_type: Literal["lookbehind"] = "lookbehind"
    positive: bool = Field(
        description="True for positive (?<=), False for negative (?<!)."
    )
    body: BCQLNode = Field(description="The sub-query to match behind.")

    def to_bcql(self) -> str:
        op = "?<=" if self.positive else "?<!"
        return f"({op} {self.body.to_bcql()})"
