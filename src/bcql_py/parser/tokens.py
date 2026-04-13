from dataclasses import dataclass
from enum import StrEnum, auto


class TokenType(StrEnum):
    # Literals
    STRING = auto()  # "hello", 'world'
    LITERAL_STRING = auto()  # l"e.g.", l'fo.o'
    INTEGER = auto()  # 123, -5
    IDENTIFIER = auto()  # word, lemma, pos, meet, union, ...

    # Brackets
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LCURLY = auto()  # {
    RCURLY = auto()  # }
    LPAREN = auto()  # (
    RPAREN = auto()  # )

    # Lookaround openers (single tokens for multiple characters, for easier parsing)
    LOOKAHEAD_POS = auto()  # (?=
    LOOKAHEAD_NEG = auto()  # (?!
    LOOKBEHIND_POS = auto()  # (?<=
    LOOKBEHIND_NEG = auto()  # (?<!

    # XML-like angle brackets
    LT = auto()  # <     (opening angle bracket, not followed by / )
    GT = auto()  # >
    LT_SLASH = auto()  # </    (opening of end-tag)
    SLASH_GT = auto()  # />    (self-closing)
    SLASH = auto()  # /     (standalone, if needed)

    # Operators: relation / alignment arrows
    ARROW = auto()  # -type-> (value holds the relation type between the dashes)
    ROOT_ARROW = auto()  # ^-type-> (root relation; value holds the relation type)


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
