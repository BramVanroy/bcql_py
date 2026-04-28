from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto


class TokenType(StrEnum):
    # Literals
    STRING = auto()  # "hello", 'world'
    LITERAL_STRING = auto()  # l"e.g.", l'fo.o'
    INTEGER = auto()  # 123, -5
    IDENTIFIER = auto()  # word, lemma, pos; fn name: meet, union, ...

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

# Maps boolean-operator token types to their string representation.
# Matches the ``booleanOperator`` rule in ``Bcql.g4``: ``'&' | '|' | '->'``.
BOOL_OPS: dict[TokenType, str] = {
    TokenType.AMP: "&",
    TokenType.PIPE: "|",
    TokenType.REL_ARROW: "->",
}

# Maps comparison-operator token types to their string representation.
# Matches the ``comparisonOperator`` rule in ``Bcql.g4``: ``'=' | '!=' | '>=' | '<=' | '>' | '<'``.
CMP_OPS: dict[TokenType, str] = {
    TokenType.EQ: "=",
    TokenType.NEQ: "!=",
    TokenType.LT: "<",
    TokenType.LTE: "<=",
    TokenType.GT: ">",
    TokenType.GTE: ">=",
}

# User-friendly display strings for each ``TokenType``. Used in syntax error messages so that
# users (or LLMs) see the actual character (``']'``) rather than the internal token name
# (``RBRACKET``). Concrete-value tokens (``STRING``, ``IDENTIFIER``, ``INTEGER``,
# ``LITERAL_STRING``) are shown as a category word without quotes so callers can
# append the actual value separately.
_TOKEN_DISPLAY: dict[TokenType, str] = {
    TokenType.STRING: "string",
    TokenType.LITERAL_STRING: "literal string",
    TokenType.INTEGER: "integer",
    TokenType.IDENTIFIER: "identifier",
    TokenType.LBRACKET: "'['",
    TokenType.RBRACKET: "']'",
    TokenType.LBRACE: "'{'",
    TokenType.RBRACE: "'}'",
    TokenType.LPAREN: "'('",
    TokenType.RPAREN: "')'",
    TokenType.LOOKAHEAD_POS: "'(?='",
    TokenType.LOOKAHEAD_NEG: "'(?!'",
    TokenType.LOOKBEHIND_POS: "'(?<='",
    TokenType.LOOKBEHIND_NEG: "'(?<!'",
    TokenType.LT: "'<'",
    TokenType.GT: "'>'",
    TokenType.LT_SLASH: "'</'",
    TokenType.SLASH_GT: "'/>'",
    TokenType.FWD_SLASH: "'/'",
    TokenType.REL_LINE: "'-'",
    TokenType.REL_ARROW: "'->'",
    TokenType.ROOT_REL_CARET: "'^'",
    TokenType.ALIGN_LINE: "'='",
    TokenType.ALIGN_ARROW: "'=>'",
    TokenType.QUESTION: "'?'",
    TokenType.LTE: "'<='",
    TokenType.GTE: "'>='",
    TokenType.EQ: "'='",
    TokenType.NEQ: "'!='",
    TokenType.BANG: "'!'",
    TokenType.AMP: "'&'",
    TokenType.PIPE: "'|'",
    TokenType.COLON: "':'",
    TokenType.DOUBLE_COLON: "'::'",
    TokenType.SEMICOLON: "';'",
    TokenType.DOT: "'.'",
    TokenType.COMMA: "','",
    TokenType.STAR: "'*'",
    TokenType.PLUS: "'+'",
    TokenType.WITHIN: "'within'",
    TokenType.CONTAINING: "'containing'",
    TokenType.OVERLAP: "'overlap'",
    TokenType.IN: "'in'",
    TokenType.TRUE: "'true'",
    TokenType.FALSE: "'false'",
    TokenType.UNDERSCORE: "'_'",
    TokenType.EOF: "end of input",
}


def display_type(ttype: TokenType) -> str:
    """Return a user-friendly representation of a ``TokenType`` for error messages.

    Concrete punctuation and keywords are shown quoted (e.g. ``"']'"``, ``"'within'"``); literal
    categories are shown as a bare word (e.g. ``"string"``, ``"identifier"``). Falls back to the
    internal name if a future ``TokenType`` is added without a display entry.

    Args:
        ttype: The token type to format.

    Returns:
        A short, human-readable label suitable for inclusion in a syntax error message.
    """
    return _TOKEN_DISPLAY.get(ttype, ttype.name)


def display_token(tok: "Token") -> str:
    """Return a user-friendly representation of a concrete ``Token`` for error messages.

    For category tokens (string, identifier, integer) the actual value is appended so the user can
    see what they typed (``"identifier 'word'"``). For symbols and keywords the raw value is shown
    quoted (``"'['"``). ``EOF`` becomes ``"end of input"``.

    Args:
        tok: The token to format.

    Returns:
        A short, human-readable description of the token, suitable for ``"got X"`` clauses
    """
    if tok.type == TokenType.EOF:
        return "end of input"
    if tok.type in (TokenType.STRING, TokenType.LITERAL_STRING):
        prefix = "literal string" if tok.type == TokenType.LITERAL_STRING else "string"
        return f"{prefix} {tok.value!r}"
    if tok.type == TokenType.IDENTIFIER:
        return f"identifier {tok.value!r}"
    if tok.type == TokenType.INTEGER:
        return f"integer {tok.value!r}"
    return repr(tok.value)


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


__all__ = ["TokenType", "Token", "KEYWORDS", "BOOL_OPS", "CMP_OPS", "display_type", "display_token"]
