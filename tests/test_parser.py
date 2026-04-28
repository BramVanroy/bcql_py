import pytest

from bcql_py.parser import BCQLLexer, BCQLParser


class TestParserReadOnlyState:
    def test_public_properties_are_read_only(self):
        # NOTE: intentional ``setattr`` over parser.tokens = ... to
        # satisfy mypy's read-only property checks, which would otherwise prevent the test from running.
        lexer = BCQLLexer("lemma")
        parser = BCQLParser(lexer.tokens, source="lemma")

        with pytest.raises(AttributeError):
            setattr(parser, "source", "word")

        with pytest.raises(AttributeError):
            setattr(parser, "pos", 10)

        with pytest.raises(AttributeError):
            setattr(parser, "tokens", ())
