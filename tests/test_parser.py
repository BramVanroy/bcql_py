import pytest

from bcql_py.parser import (
    BCQLLexer,
    BCQLParser,
    CorpusSpec,
    TokenType,
    parse,
    parse_from_tokens,
)
from bcql_py.validation import BCQLValidationError


class TestParserProperties:
    """Parser property and cache behavior tests."""

    def test_public_properties_are_read_only(self):
        """Parser public properties are read-only after construction."""
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

    def test_parser_basic_properties_and_ast_cache_paths(self):
        """Parser exposes source/position/tokens and caches the parsed AST."""
        parser = BCQLParser(BCQLLexer("_").tokenize(), source="_")

        assert parser.source == "_"
        assert parser.pos == 0
        assert parser.tokens[-1].type == TokenType.EOF

        ast_first = parser.ast
        ast_second = parser.ast
        assert ast_first is ast_second

        parse_first = parser.parse()
        parse_second = parser.parse()
        assert parse_first is parse_second

    def test_bcql_cached_property_delegates_to_to_bcql(self):
        """`BCQLNode.bcql` delegates to `to_bcql()` for serialized output."""
        ast = parse('[word="hello"]')
        assert ast.bcql == ast.to_bcql()

    def test_parser_parse_can_force_reparse(self):
        """`force_reparse=True` bypasses the cached AST and returns a fresh node."""
        parser = BCQLParser(BCQLLexer("_").tokenize(), source="_")
        original = parser.parse()
        parser._pos = 0

        reparsed = parser.parse(force_reparse=True)

        # Functionally equivalent but not the same object, since the cache is bypassed.
        assert reparsed is not original


class TestParserWithSpec:
    """Parser integration tests when semantic validation spec is provided."""

    def test_parse_from_tokens_with_spec_runs_validation(self):
        """`parse_from_tokens(..., spec=...)` runs validation and raises on violations."""
        spec = CorpusSpec(closed_attributes={"pos": {"NOUN"}})
        tokens = BCQLLexer('[pos="BOGUS"]').tokenize()

        with pytest.raises(BCQLValidationError):
            parse_from_tokens(tokens, source='[pos="BOGUS"]', spec=spec)
