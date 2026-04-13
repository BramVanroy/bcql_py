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

    def _peek_ahead_char(self, offset: int = 1) -> str:
        if self.pos + offset < len(self.source):
            return self.source[self.pos + offset]
        return ""

    def _peek_ahead_string(self, length: int) -> str:
        return self.source[self.pos : self.pos + length]

    def _step(self, steps: int = 1) -> str:
        result = self.source[self.pos : self.pos + steps]
        self.pos += steps
        return result

    def _set_found_token(self, ttype: TokenType, value: str, position: int) -> None:
        self.tokens.append(Token(type=ttype, value=value, position=position))

    def _raise_error(self, msg: str) -> BCQLSyntaxError:
        return BCQLSyntaxError(msg, query=self.source, position=self.pos)

    def _skip_whitespace(self) -> None:
        while self._current_char.isspace():
            self._step()

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
        raise self._raise_error(f"Unterminated string (expected closing {initial_quote_char!r})")

    def _is_relation_arrow(self, offset: int = 0) -> bool:
        """Check if from current pos + offset we have ``-type->`` pattern."""
        start_char_idx = self.pos + offset
        if start_char_idx >= len(self.source) or self.source[start_char_idx] != "-":
            return False
        start_char_idx += 1  # skip initial '-'

        while start_char_idx < len(self.source):
            ch = self.source[start_char_idx]
            # Found '->' pattern, so this is a relation arrow
            if ch == "-" and start_char_idx + 1 < len(self.source) and self.source[start_char_idx + 1] == ">":
                return True
            # If we encounter whitespace or a closing bracket before finding '->', this cannot be a relation arrow
            if ch in " \t\n\r)]}":
                return False
            start_char_idx += 1
        return False

    def _read_relation_arrow(self, start: int, is_root: bool = False) -> None:
        """Read ``-type->`` after the leading ``-`` has been identified."""
        if is_root:
            self.pos += 1  # skip the leading '^'

        self.pos += 1  # skip the leading '-'
        # Read the relation type (everything up to '->') which may be empty
        rtype_chars: list[str] = []
        while self.pos < len(self.source):
            if self._current_char == "-" and self._peek_ahead_char() == ">":
                break
            rtype_chars.append(self._current_char)
            self.pos += 1
        else:
            raise self._error("Expected '->' to close relation arrow")

        self.pos += 2  # skip '->'

        rtype = "".join(rtype_chars)
        if is_root:
            self._set_found_token(TokenType.ROOT_ARROW, rtype, start)
        else:
            self._set_found_token(TokenType.ARROW, rtype, start)

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
            # 1. Simple strings
            # 1.1. Quoted strings (both single and double)
            if curr_char in ('"', "'"):
                # Read string
                self._read_string(curr_char, starting_pos, is_literal=False)
                continue

            # 1.2. "literal" tokens, e.g. `l"e.g."`
            # Note that in alternative notation, one can escape the period with a backslash without the need of a literal `l` flag, e.g. `"e\.g\."`
            if curr_char == "l" and self._peek_ahead_char() in ('"', "'"):
                self.pos += 1  # skip 'l'
                # Read internal string; re-call self._current_char after pos updated
                self._read_string(self._current_char, starting_pos, is_literal=True)
                continue

            # 2. Brackets
            # 2.1. Square brackets
            if curr_char == "[":
                self._set_found_token(TokenType.LBRACKET, curr_char, starting_pos)
                self.pos += 1
                continue
            if curr_char == "]":
                self._set_found_token(TokenType.RBRACKET, curr_char, starting_pos)
                self.pos += 1
                continue

            # 2.2. Curly Brackets (e.g. for grouping in regexes), example: `{2,3}`
            if curr_char == "{":
                self._set_found_token(TokenType.LCURLY, curr_char, starting_pos)
                self.pos += 1
                continue
            if curr_char == "}":
                self._set_found_token(TokenType.RCURLY, curr_char, starting_pos)
                self.pos += 1
                continue

            # 2.3. Parentheses
            if curr_char == "(":
                # Check first if it is part of a regex look-around
                # i.e. look-behind: `(?<=...)`, `(?<!...)`, look-ahead: `(?=...)`, `(?!...)`
                rest4 = self._peek_ahead_string(4)
                if rest4 == "(?<=":
                    self._set_found_token(TokenType.LOOKBEHIND_POS, rest4, starting_pos)
                    self.pos += 4
                    continue
                if rest4 == "(?<!":
                    self._set_found_token(TokenType.LOOKBEHIND_NEG, rest4, starting_pos)
                    self.pos += 4
                    continue

                rest3 = self._peek_ahead_string(3)
                if rest3 == "(?=":
                    self._set_found_token(TokenType.LOOKAHEAD_POS, rest3, starting_pos)
                    self.pos += 3
                    continue
                if rest3 == "(?!":
                    self._set_found_token(TokenType.LOOKAHEAD_NEG, rest3, starting_pos)
                    self.pos += 3
                    continue

                # If not a lookaround, treat as normal parenthesis
                self._set_found_token(TokenType.LPAREN, "(", starting_pos)
                self.pos += 1
                continue

            if curr_char == ")":
                self._set_found_token(TokenType.RPAREN, ")", starting_pos)
                self.pos += 1
                continue

            # 2.4. Angled brackets, e.g. for XML
            # TODO: are named groups in regexes also supported, e.g. `(?P<name>...)` in BlackLab?
            if curr_char == "<":
                if self._peek_ahead_char() == "/":
                    self._set_found_token(TokenType.LT_SLASH, "</", starting_pos)
                    self.pos += 2
                    continue
                self._set_found_token(TokenType.LT, "<", starting_pos)
                self.pos += 1
                continue
            if curr_char == ">":
                self._set_found_token(TokenType.GT, ">", starting_pos)
                self.pos += 1
                continue
            if curr_char == "/" and self._peek_ahead_char() == ">":
                self._set_found_token(TokenType.SLASH_GT, "/>", starting_pos)
                self.pos += 2
                continue

            # 3. Relations
            # 3.1. Minus sign or dash `-` :  could be relation arrow or negative int -
            if curr_char == "-":
                # 3.1.1. Check if this is a relation arrow: -type->
                # A relation arrow starts with '-' and somewhere later has '->'
                if self._is_relation_arrow():
                    self._read_relation_arrow(starting_pos)
                    continue

                # 3.1.2. Negative integer
                if self._peek_ahead_char().isdigit():
                    self.pos += 1
                    int_start = starting_pos
                    chars = ["-"]
                    while self.pos < len(self.source) and self._current_char.isdigit():
                        chars.append(self._current_char)
                        self.pos += 1
                    self._set_found_token(TokenType.INTEGER, "".join(chars), int_start)
                    continue

                # If it's neither a relation arrow nor a negative integer, it's an unexpected character in this context
                raise self._raise_error("Unexpected character '-'")

            # 3.2. Root relation arrow, e.g. `^-obj->` or `^-->` (if no relation type specified)
            if curr_char == "^" and self._is_relation_arrow(offset=1):
                self._read_relation_arrow(starting_pos, is_root=True)
                continue

        return self.tokens
