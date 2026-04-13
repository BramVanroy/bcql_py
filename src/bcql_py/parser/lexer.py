from __future__ import annotations

class BCQLLexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self._pos = 0
        self.tokens: list[str] = []
    
    @property
    def _current_char(self) -> str:
        if self._pos < len(self.source):
            return self.source[self._pos]
        return ""
    
    def _peak_ahead_char(self, offset: int = 1) -> str:
        if self._pos + offset < len(self.source):
            return self.source[self._pos + offset]
        return ""
    
    def _peak_ahead_string(self, length: int) -> str:
        return self.source[self._pos:self._pos + length]
    
    def _advance(self, steps: int = 1) -> None:
        result = self.source[self._pos : self._pos + steps]
        self._pos += steps
        return result
    
    def _set_found_token(self, value: str) -> None:
        self.tokens.append(value)
    
    def throw_error(self, message: str) -> None:
        raise SyntaxError(f"Lexer error at position {self._pos}: {message}")
    
    def _skip_whitespace(self) -> None:
        while self._current_char.isspace():
            self._advance()
    
    def tokenize(self) -> list[str]:
        while self._pos < len(self.source):
            self._skip_whitespace()
            if self._current_char.isalpha() or self._current_char == "_":
                self._tokenize_identifier()
            elif self._current_char.isdigit():
                self._tokenize_number()
            elif self._current_char in ('"', "'"):
                self._tokenize_string()
            else:
                self.throw_error(f"Unexpected character: {self._current_char}")
        return self.tokens