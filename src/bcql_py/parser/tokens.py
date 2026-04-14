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
    REL_ARROW = auto()  # ->
    ROOT_REL_CARET = auto()
    ALIGN_LINE = auto()  # =type= (alignment line, no field)
    ALIGN_ARROW = auto()  # =>
    QUESTION = auto()  # ? (eg optional alignment, after field, e.g. ==>nl?; regex quantifier)

    # Operators: comparison
    LTE = auto()  # <=
    GTE = auto()  # >=
    EQ = auto()  # =
    NEQ = auto()  # !=
    LT_CMP = auto()  # <
    GT_CMP = auto()  # >

    # Operators: logical / boolean
    BANG = auto()  # !  (standalone negation)
    AMP = auto()  # &
    PIPE = auto()  # |

    # Operators: misc
    COLON = auto()  # :
    DOUBLE_COLON = auto()  # :: (constraints)
    SEMICOLON = auto()  # ;
    DOT = auto()  # .
    COMMA = auto()  # ,

    # Quantifiers
    STAR = auto()  # *
    PLUS = auto()  # +
    # See QUESTION above for ?

    # Reserved
    WITHIN = auto()
    CONTAINING = auto()
    OVERLAP = auto()
    IN = auto()
    TRUE = auto()
    FALSE = auto()
    UNDERSCORE = auto()  # _ (matches any single token)
    # End marker
    EOF = auto()  # end of input


# https://github.com/instituutnederlandsetaal/BlackLab/blob/e248fc2acf2b8cf44deb2564e8b24138b140d4ca/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4#L24
KEYWORDS: dict[str, TokenType] = {
    "within": TokenType.WITHIN,
    "containing": TokenType.CONTAINING,
    "overlap": TokenType.OVERLAP,
    "in": TokenType.IN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "_": TokenType.UNDERSCORE,
}


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
