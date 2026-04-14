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
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    LPAREN = auto()  # (
    RPAREN = auto()  # )

    # Lookaround openers
    LOOKAHEAD_POS = auto()  # (?=
    LOOKAHEAD_NEG = auto()  # (?!
    LOOKBEHIND_POS = auto()  # (?<=
    LOOKBEHIND_NEG = auto()  # (?<!

    # XML-like angle brackets
    LT = auto()  # <     (opening angle bracket, not followed by / )
    GT = auto()  # >
    LT_SLASH = auto()  # </    (opening of end-tag)
    SLASH_GT = auto()  # />    (self-closing)
    FWD_SLASH = auto()  # /     (standalone, if needed)

    # Operators: relation / alignment arrows
    REL_LINE = auto()  # -
    REL_ARROW = auto() # ->
    ROOT_REL_CARET = auto()
    ALIGN_LINE = auto()  # =type= (alignment line, no field)
    ALIGN_ARROW = auto()  # =>
    QUESTION = auto()  # ? (eg optional alignment, after field, e.g. ==>nl?)

    # Operators: comparison
    EQ = auto()  # =
    NEQ = auto()  # !=
    LT_CMP = auto()  # <
    LE = auto()  # <=
    GT_CMP = auto()  # >
    GE = auto()  # >=


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
