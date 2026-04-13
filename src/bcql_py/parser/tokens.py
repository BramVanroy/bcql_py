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
    # Rather than storing the relation type in the Token.value,
    # the full string is stored, e.g. "-rel->" or "=word=>nl", and the TokenType indicates the kind of arrow.
    # The actual decoding of relation type, target field etc. is deferred to the parser
    ARROW = auto()
    ROOT_ARROW = auto()
    ALIGNMENT = auto()

    # Operators: comparison
    EQ = auto()  # =
    NEQ = auto()  # !=
    LT_CMP = auto()  # < (comparison, inside constraints)
    LE = auto()  # <=
    GT_CMP = auto()  # > (comparison, inside constraints)
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
