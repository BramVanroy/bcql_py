"""Base class for all BCQL AST nodes.

Every node in the parsed BCQL tree inherits from BCQLNode. The class
is a frozen Pydantic v2 ``BaseModel`` (immutable after construction) with a
``node_type`` discriminator field. which we can use later to reconstruct the original query string.
"""

from __future__ import annotations

import abc
from functools import cached_property

from pydantic import BaseModel, ConfigDict


class BCQLNode(BaseModel, abc.ABC):
    """Abstract base for every node in the BCQL abstract syntax tree.

    Sub-classes **must** override :pymethod:`to_bcql` and set ``node_type``
    to a unique ``Literal`` string so that discrimination works correctly

    Configuration:
      - ``frozen = True``: instances are immutable after creation
      - ``use_enum_values = True``: enum fields store their ``.value``
    """

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    @abc.abstractmethod
    def to_bcql(self) -> str:
        """Reconstruct a BCQL query string from this AST node.

        The returned string is *functionally* equivalent to the original
        query but may differ in trivial whitespace and formatting.
        """

    @cached_property
    def bcql(self) -> str:
        """Convenience property to get the BCQL string representation of this node."""
        return self.to_bcql()
