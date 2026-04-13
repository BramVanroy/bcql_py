from dataclasses import dataclass
from enum import StrEnum, auto


class TokenType(StrEnum):
    STRING = auto()
    LITERAL_STRING = auto()


@dataclass(frozen=True, slots=True)
class Token:
    """A single token produced by the BCQL lexer.

    Attributes:
        type: The [TokenType][bcql_py.parser.tokens.TokenType] of this token.
        value: The raw string content of the token.
        position: The 0-based character offset in the source string.
    """

    type: TokenType
    value: str
    position: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, pos={self.position})"
