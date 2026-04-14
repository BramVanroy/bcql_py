"""Tests for parser error reporting: syntax errors with position information."""

import pytest
from conftest import parse

from bcql_py.exceptions import BCQLSyntaxError


class TestParserErrors:
    """Syntax errors should include position information."""

    def test_unclosed_bracket(self):
        with pytest.raises(BCQLSyntaxError, match="after annotation name"):
            parse("[word")

    def test_missing_value(self):
        with pytest.raises(BCQLSyntaxError, match="string"):
            parse("[word=]")

    def test_empty_input(self):
        with pytest.raises(BCQLSyntaxError):
            parse("")

    def test_unknown_token_in_atom(self):
        with pytest.raises(BCQLSyntaxError):
            parse("&")

    def test_error_has_position(self):
        with pytest.raises(BCQLSyntaxError) as exc_info:
            parse("[word=]")
        assert exc_info.value.position is not None
