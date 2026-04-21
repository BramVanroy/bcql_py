"""Function calls as func-args nodes"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bcql_py.models.base import BCQLNode


__all__ = ["FunctionCallNode"]


class FunctionCallNode(BCQLNode):
    """A built-in function call at the sequence level.

    Function arguments can be sub-queries BCQLNode, tring values StringValue, or integers

    Attributes:
        name: Function name
        args: Positional arguments
    """

    node_type: Literal["function_call"] = "function_call"
    name: str = Field(description="Function name")
    args: list[BCQLNode | int] = Field(description="Positional arguments")

    def to_bcql(self) -> str:
        parts: list[str] = []
        for arg in self.args:
            if isinstance(arg, int):
                parts.append(str(arg))
            elif isinstance(arg, BCQLNode):
                parts.append(arg.to_bcql())
            else:
                raise ValueError(f"Invalid argument type: {type(arg)}. Expected (subclass of) BCQLNode or int.")
        return f"{self.name}({', '.join(parts)})"
