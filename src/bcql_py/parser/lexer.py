from __future__ import annotations

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.parser.tokens import Token, TokenType


class BCQLLexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.tokens: list[Token] = []

    @property
    def _current_char(self) -> str:
        return self.source[self.pos]

    def _peak_ahead_char(self, offset: int = 1) -> str:
        if self.pos + offset < len(self.source):
            return self.source[self.pos + offset]
        return ""

    def _peak_ahead_string(self, length: int) -> str:
        return self.source[self.pos : self.pos + length]

    def _advance(self, steps: int = 1) -> None:
        result = self.source[self.pos : self.pos + steps]
        self.pos += steps
        return result

    def _set_found_token(self, ttype: TokenType, value: str, position: int) -> None:
        token = Token(type=ttype, value=value, position=position)
        self.tokens.append(token)

    def _throw_error(self, msg: str) -> BCQLSyntaxError:
        return BCQLSyntaxError(msg, query=self.source, position=self.pos)

    def _skip_whitespace(self) -> None:
        while self._current_char.isspace():
            self._advance()

    def _read_string(self, initial_quote_char: str, starting_pos: int, is_literal: bool) -> None:
        """Read a quoted string, handling escape sequences."""
        self.pos += 1  # skip opening quote
        chars: list[str] = []
        while self.pos < len(self.source):
            char = self.source[self.pos]
            # Handle escape sequences (e.g., \" or \'), e.g. `"e\.g\."`
            if char == "\\" and self.pos + 1 < len(self.source):
                # Preserve the backslash-escaped character as-is
                chars.append(char)
                chars.append(self.source[self.pos + 1])
                self.pos += 2
            elif char == initial_quote_char:
                self.pos += 1  # skip closing quote
                ttype = TokenType.LITERAL_STRING if is_literal else TokenType.STRING
                self._set_found_token(ttype, "".join(chars), starting_pos)
                return
            else:
                chars.append(char)
                self.pos += 1
        raise self._error(f"Unterminated string (expected closing {initial_quote_char!r})")

    def tokenize(self) -> list[Token]:
        """
        We assume the base case where the token can be a sequence of `[]` tokens or `""` or `''` or a sequence of alphanumeric characters and underscores.
        """
        while self.pos < len(self.source):
            self._skip_whitespace()

            if self.pos >= len(self.source):
                break

            starting_pos = self.pos
            curr_char = self._current_char
            # Quoted strings (both single and double)
            if curr_char in ('"', "'"):
                # Read string
                self._read_string(curr_char, starting_pos, is_literal=False)
                continue

            # "literal" tokens, e.g. `l"e.g."`
            # Note that in alternative notation, one can escape the period with a backslash without the need of a literal `l` flag, e.g. `"e\.g\."`
            elif curr_char == "l" and self._peak_ahead_char() in ('"', "'"):
                self.pos += 1  # skip 'l'
                # Read internal string; re-call self._current_char after pos updated
                self._read_string(self._current_char, starting_pos, is_literal=True)
                continue

        return self.tokens
