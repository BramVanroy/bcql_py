import pytest

from bcql_py.parser import BCQLLexer, BCQLParser


class TestParserReadOnlyState:
    def test_public_properties_are_read_only(self):
        lexer = BCQLLexer("lemma")
        parser = BCQLParser(lexer.tokens, source="lemma")

        with pytest.raises(AttributeError):
            parser.source = "word"

        with pytest.raises(AttributeError):
            parser.pos = 10

        with pytest.raises(AttributeError):
            parser.tokens = []
