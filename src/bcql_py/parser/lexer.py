from __future__ import annotations

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.parser.tokens import KEYWORDS, Token, TokenType


class BCQLLexer:
    __slots__ = ("_source", "_pos", "_tokens")

    def __init__(self, source: str) -> None:
        self._source = source
        self._pos = 0
        self._tokens: list[Token] = []

    @property
    def source(self) -> str:
        return self._source

    @property
    def pos(self) -> int:
        return self._pos

    @property
    def tokens(self) -> tuple[Token, ...]:
        # Return a tuple to prevent accidental modification of the token list from outside the lexer
        return tuple(self._tokens)

    @property
    def _current_char(self) -> str:
        return self._source[self._pos]

    def _peek_char(self, offset: int = 1) -> str:
        if self._pos + offset < len(self._source):
            return self._source[self._pos + offset]
        return ""

    def _peek_str(self, length: int) -> str:
        return self._source[self._pos : self._pos + length]

    def _step(self, steps: int = 1) -> str:
        result = self._source[self._pos : self._pos + steps]
        self._pos += steps
        return result

    def _emit(self, ttype: TokenType, value: str, position: int) -> None:
        self._tokens.append(Token(type=ttype, value=value, position=position))

    def _raise_error(self, msg: str) -> BCQLSyntaxError:
        return BCQLSyntaxError(error_message=msg, bcql_query=self._source, error_position=self._pos)

    def _skip_whitespace(self) -> None:
        while self._current_char.isspace():
            self._step()

    def _read_string(self, initial_quote_char: str, starting_pos: int, is_literal: bool) -> None:
        """Read a quoted string, handling escape sequences."""
        self._pos += 1  # skip opening quote
        chars: list[str] = []
        while self._pos < len(self._source):
            char = self._source[self._pos]
            # Handle escape sequences (e.g., \" or \'), e.g. `"e\.g\."`
            if char == "\\" and self._pos + 1 < len(self._source):
                # Preserve the backslash-escaped character as-is
                chars.append(char)
                chars.append(self._source[self._pos + 1])
                self._pos += 2
            elif char == initial_quote_char:
                self._pos += 1  # skip closing quote
                ttype = TokenType.LITERAL_STRING if is_literal else TokenType.STRING
                self._emit(ttype, "".join(chars), starting_pos)
                return
            else:
                chars.append(char)
                self._pos += 1
        raise self._raise_error(f"Unterminated string (expected closing {initial_quote_char!r})")

    def _is_arrow(self, offset: int = 0, is_parallel_relation: bool = False) -> bool:
        """Check if from current pos + offset we have ``-type->`` or ``=type=>`` pattern."""
        line_char = "=" if is_parallel_relation else "-"
        start_char_idx = self._pos + offset
        if start_char_idx >= len(self._source) or self._source[start_char_idx] != line_char:
            return False
        start_char_idx += 1  # skip initial '-'

        while start_char_idx < len(self._source):
            ch = self._source[start_char_idx]
            # Found '->' pattern, so this is a relation arrow
            if ch == line_char and start_char_idx + 1 < len(self._source) and self._source[start_char_idx + 1] == ">":
                return True
            # If we encounter whitespace or a closing bracket before finding '->', this cannot be a relation arrow
            if ch in " \t\n\r)]}":
                return False
            start_char_idx += 1
        return False

    def _read_arrow(self, start: int, is_root: bool = False, is_parallel_relation: bool = False) -> None:
        """Read ``-type->`` or ``=type=>`` after the leading ``-`` or ``=`` (=True) has been identified."""
        if is_root:
            self._pos += 1  # skip the leading '^'

        if is_root and is_parallel_relation:
            raise self._raise_error("Root relations cannot be parallel (i.e. start with '^')")

        line_char = "=" if is_parallel_relation else "-"
        self._pos += 1  # skip the leading '-' or '='
        # Read the relation type (everything up to '->') which may be empty
        rtype_chars: list[str] = []
        while self._pos < len(self._source):
            if self._current_char == line_char and self._peek_char() == ">":
                break
            rtype_chars.append(self._current_char)
            self._pos += 1
        else:
            raise self._raise_error("Expected '->' or '=>' to close relation arrow")

        self._pos += 2  # skip '->' or '=>'

        rtype = "".join(rtype_chars)

        # Check for target field suffix in parallel relations, we can have `=type=>field`
        # See https://github.com/instituutnederlandsetaal/BlackLab/blob/dev/site/docs/guide/040_query-language/030_parallel.md
        # TODO: check if this exclusive to parallel relations
        field = ""
        if self._pos < len(self._source) and self._current_char.isalpha():
            field_start = self._pos
            while self._pos < len(self._source) and (
                self._current_char.isalnum() or self._current_char == "_" or self._current_char == "?"
            ):
                self._pos += 1
            field = self._source[field_start : self._pos]

        if is_root:
            self._emit(TokenType.ROOT_REL_CARET, "^", start)
            start += 1

        if is_parallel_relation:
            self._emit(TokenType.ALIGN_LINE, "=", start)
        else:
            self._emit(TokenType.REL_LINE, "-", start)
        start += 1

        if rtype:
            self._emit(TokenType.IDENTIFIER, rtype, start)
            start += len(rtype)

        if is_parallel_relation:
            self._emit(TokenType.ALIGN_ARROW, "=>", start)
        else:
            self._emit(TokenType.REL_ARROW, "->", start)
        start += 2

        if field:
            if is_optional := field.endswith("?"):
                field = field[:-1]
            if field == "_":
                self._emit(TokenType.UNDERSCORE, "_", start)
            else:
                self._emit(TokenType.IDENTIFIER, field, start)
            start += len(field)
            if is_optional:
                self._emit(TokenType.QUESTION, "?", start)

    def _is_alignment_arrow(self, offset: int = 0) -> bool:
        """Check if from current pos + offset we have ``=type=>field[?]`` pattern."""
        return self._is_arrow(offset=offset, is_parallel_relation=True)

    def _read_alignment_arrow(self, start: int) -> None:
        """Read ``=type=>field[?]`` starting from the first ``=``."""
        self._read_arrow(start, is_root=False, is_parallel_relation=True)

    def _read_identifier(self, start: int) -> None:
        """Read an identifier, incl. reserved keywords."""
        chars: list[str] = []
        while self._pos < len(self._source) and (self._current_char.isalnum() or self._current_char in "_-"):
            chars.append(self._current_char)
            self._pos += 1

        word = "".join(chars)
        # Try getting a reserved keyword match, otherwise default to IDENTIFIER
        ttype = KEYWORDS.get(word, TokenType.IDENTIFIER)
        self._emit(ttype, word, start)

    def _read_integer(self, start: int) -> None:
        """Read an integer (possibly negative, though sign is separate)."""
        chars: list[str] = []
        if self._current_char == "-":
            chars.append("-")
            self._pos += 1
        while self._pos < len(self._source) and self._current_char.isdigit():
            chars.append(self._current_char)
            self._pos += 1
        self._emit(TokenType.INTEGER, "".join(chars), start)

    def tokenize(self) -> tuple[Token]:
        """
        We assume the base case where the token can be a sequence of `[]` tokens or `""` or `''` or a sequence of alphanumeric characters and underscores.
        """
        while self._pos < len(self._source):
            self._skip_whitespace()

            if self._pos >= len(self._source):
                break

            starting_pos = self._pos
            curr_char = self._current_char

            # Quoted strings (both single and double)
            if curr_char in ('"', "'"):
                self._read_string(curr_char, starting_pos, is_literal=False)
                continue

            # "literal" tokens, e.g. `l"e.g."`
            # Note that in alternative notation, one can escape the period with a backslash without the need of a literal `l` flag, e.g. `"e\.g\."`
            if curr_char == "l" and self._peek_char() in ('"', "'"):
                self._pos += 1  # skip 'l'
                # re-call self._current_char after pos updated
                self._read_string(self._current_char, starting_pos, is_literal=True)
                continue

            # Square brackets
            if curr_char == "[":
                self._emit(TokenType.LBRACKET, curr_char, starting_pos)
                self._pos += 1
                continue
            if curr_char == "]":
                self._emit(TokenType.RBRACKET, curr_char, starting_pos)
                self._pos += 1
                continue

            # Curly Brackets (e.g. for grouping in regexes), example: `{2,3}`
            if curr_char == "{":
                self._emit(TokenType.LBRACE, curr_char, starting_pos)
                self._pos += 1
                continue
            if curr_char == "}":
                self._emit(TokenType.RBRACE, curr_char, starting_pos)
                self._pos += 1
                continue

            # Parentheses
            if curr_char == "(":
                # Check first if it is part of a regex look-around
                # i.e. look-behind: `(?<=...)`, `(?<!...)`, look-ahead: `(?=...)`, `(?!...)`
                rest4 = self._peek_str(4)
                if rest4 == "(?<=":
                    self._emit(TokenType.LOOKBEHIND_POS, rest4, starting_pos)
                    self._pos += 4
                    continue
                if rest4 == "(?<!":
                    self._emit(TokenType.LOOKBEHIND_NEG, rest4, starting_pos)
                    self._pos += 4
                    continue

                rest3 = self._peek_str(3)
                if rest3 == "(?=":
                    self._emit(TokenType.LOOKAHEAD_POS, rest3, starting_pos)
                    self._pos += 3
                    continue
                if rest3 == "(?!":
                    self._emit(TokenType.LOOKAHEAD_NEG, rest3, starting_pos)
                    self._pos += 3
                    continue

                # If not a lookaround, treat as normal parenthesis
                self._emit(TokenType.LPAREN, "(", starting_pos)
                self._pos += 1
                continue

            if curr_char == ")":
                self._emit(TokenType.RPAREN, ")", starting_pos)
                self._pos += 1
                continue

            # Angled brackets, e.g. for XML
            # TODO: are named groups in regexes also supported, e.g. `(?P<name>...)` in BlackLab?
            if curr_char == "<":
                if self._peek_char() == "/":
                    self._emit(TokenType.LT_SLASH, "</", starting_pos)
                    self._pos += 2
                    continue

                if self._peek_char() == "=":
                    self._emit(TokenType.LTE, "<=", starting_pos)
                    self._pos += 2
                    continue

                self._emit(TokenType.LT, "<", starting_pos)
                self._pos += 1
                continue

            if curr_char == ">":
                if self._peek_char() == "=":
                    self._emit(TokenType.GTE, ">=", starting_pos)
                    self._pos += 2
                    continue

                self._emit(TokenType.GT, ">", starting_pos)
                self._pos += 1
                continue
            if curr_char == "/" and self._peek_char() == ">":
                self._emit(TokenType.SLASH_GT, "/>", starting_pos)
                self._pos += 2
                continue

            # Minus sign or dash `-`:  could be relation arrow or negative int -
            if curr_char == "-":
                # Check if this is a relation arrow: -type->
                # A relation arrow starts with '-' and somewhere later has '->'
                if self._is_arrow():
                    self._read_arrow(starting_pos)
                    continue

                # Negative integer
                if self._peek_char().isdigit():
                    self._read_integer(starting_pos)
                    continue

                # If it's neither a relation arrow nor a negative integer, it's an unexpected character in this context
                raise self._raise_error("Unexpected character '-'")

            # Root relation arrow, e.g. `^-obj->` or `^-->` (if no relation type specified)
            if curr_char == "^":
                if self._is_arrow(offset=1):
                    self._read_arrow(starting_pos, is_root=True)
                else:
                    raise self._raise_error(
                        "Unexpected character '^' (if you meant to start a root relation, it should be followed by a relation arrow like `^-type->` or `^->`)"
                    )
                continue

            # Equals sign `=`: could be alignment arrow or just an equals sign for assigfment
            if curr_char == "=":
                if self._is_alignment_arrow():
                    self._read_alignment_arrow(starting_pos)
                    continue
                # Otherwise treat as standalone equals sign (e.g. for assignment)
                self._emit(TokenType.EQ, "=", starting_pos)
                self._pos += 1
                continue

            if curr_char == "!":
                # 3.4.1 Check if this is a not-equals operator `!=`
                if self._peek_char() == "=":
                    self._emit(TokenType.NEQ, "!=", starting_pos)
                    self._pos += 2
                    continue

                # Otherwise, treat as standalone '!' (e.g. for negation in regexes)
                self._emit(TokenType.BANG, "!", starting_pos)
                self._pos += 1
                continue

            # Logical AND and OR operators
            if curr_char == "&":
                self._emit(TokenType.AMP, "&", starting_pos)
                self._pos += 1
                continue

            if curr_char == "|":
                self._emit(TokenType.PIPE, "|", starting_pos)
                self._pos += 1
                continue

            # Colon and double colon (e.g. for constraints)
            if curr_char == ":":
                if self._peek_char() == ":":
                    self._emit(TokenType.DOUBLE_COLON, "::", starting_pos)
                    self._pos += 2
                    continue
                self._emit(TokenType.COLON, ":", starting_pos)
                self._pos += 1
                continue

            # Semicolon
            if curr_char == ";":
                self._emit(TokenType.SEMICOLON, ";", starting_pos)
                self._pos += 1
                continue

            # Dot
            if curr_char == ".":
                self._emit(TokenType.DOT, ".", starting_pos)
                self._pos += 1
                continue

            # Comma
            if curr_char == ",":
                self._emit(TokenType.COMMA, ",", starting_pos)
                self._pos += 1
                continue

            if curr_char.isdigit():
                self._read_integer(starting_pos)
                continue

            # Identifiers and keywords
            if curr_char.isalpha() or curr_char == "_":
                self._read_identifier(starting_pos)
                continue

            # Comments starting with #, skip until end of line
            if curr_char == "#":
                while self._pos < len(self._source) and self._source[self._pos] != "\n":
                    self._pos += 1
                continue

            # Multiline comments
            if curr_char == "/" and self._peek_char() == "*":
                self._pos += 2  # Skip "/*"
                while self._pos < len(self._source) and not (self._current_char == "*" and self._peek_char() == "/"):
                    self._pos += 1
                if self._pos < len(self._source):
                    self._pos += 2  # Skip "*/"
                continue

            raise self._raise_error(f"Unexpected character {curr_char!r}")
        else:
            self._emit(TokenType.EOF, "", self._pos)

        return self.tokens


def tokenize(source: str) -> tuple[Token]:
    lexer = BCQLLexer(source)
    return lexer.tokenize()
