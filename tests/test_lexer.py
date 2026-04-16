import pytest

from bcql_py.parser.lexer import BCQLLexer, BCQLSyntaxError, tokenize
from bcql_py.parser.tokens import Token, TokenType


def lex(source: str) -> list[Token]:
    """Tokenize *source* and return tokens (excl. EOF)."""
    tokens = BCQLLexer(source).tokenize()
    tokens = [token for token in tokens if token.type != TokenType.EOF]
    return tokens


class TestLexerReadOnlyState:
    def test_public_properties_are_read_only(self):
        lexer = BCQLLexer("lemma")

        with pytest.raises(AttributeError):
            lexer.source = "word"

        with pytest.raises(AttributeError):
            lexer.pos = 10

        with pytest.raises(AttributeError):
            lexer.tokens = []

    def test_tokens_property_is_immutable(self):
        lexer = BCQLLexer("lemma")
        _ = lexer.tokenize()  # Populate the tokens property

        assert isinstance(lexer.tokens, tuple)
        assert lexer.tokens[0].value == "lemma"
        assert len(lexer.tokens) == 2  # includes EOF


class TestLexerStrings:
    def test_double_quoted(self):
        tokens = lex('"hello"')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"

    def test_single_quoted(self):
        tokens = lex("'hello'")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"

    def test_literal_string(self):
        tokens = lex('l"e.g."')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LITERAL_STRING
        # Note that the 'l' prefix is not included in the token value! It's just a marker for the lexer to treat the string as literal.
        # The full string content, including any escaped characters, is stored in the token value.
        assert tokens[0].value == "e.g."

    def test_escaped_quote(self):
        tokens = lex('"say \\"yes\\""')
        assert tokens[0].value == 'say \\"yes\\"'

    def test_regex_in_string(self):
        tokens = lex('"(wo)?man"')
        assert tokens[0].value == "(wo)?man"

    def test_sensitivity_flags(self):
        tokens = lex('"(?-i)Panama"')
        assert tokens[0].value == "(?-i)Panama"


class TestLexerIdentifiers:
    def test_simple_identifier(self):
        tokens = lex("lemma")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "lemma"

    def test_keyword_within(self):
        tokens = lex("within")
        assert tokens[0].type == TokenType.WITHIN

    def test_keyword_containing(self):
        tokens = lex("containing")
        assert tokens[0].type == TokenType.CONTAINING

    def test_keyword_overlap(self):
        tokens = lex("overlap")
        assert tokens[0].type == TokenType.OVERLAP

    def test_keyword_in(self):
        tokens = lex("in")
        assert tokens[0].type == TokenType.IN

    def test_keyword_true(self):
        tokens = lex("true")
        assert tokens[0].type == TokenType.TRUE

    def test_keyword_false(self):
        tokens = lex("false")
        assert tokens[0].type == TokenType.FALSE

    def test_keyword_underscore(self):
        tokens = lex("_")
        assert tokens[0].type == TokenType.UNDERSCORE
        assert tokens[0].value == "_"

    @pytest.mark.parametrize(
        "text, expected_type",
        [
            ("WITHIN", TokenType.WITHIN),
            ("Within", TokenType.WITHIN),
            ("CONTAINING", TokenType.CONTAINING),
            ("Containing", TokenType.CONTAINING),
            ("OVERLAP", TokenType.OVERLAP),
            ("TRUE", TokenType.TRUE),
            ("True", TokenType.TRUE),
            ("FALSE", TokenType.FALSE),
            ("IN", TokenType.IN),
        ],
    )
    def test_keywords_case_insensitive(self, text, expected_type):
        """Keywords match case-insensitively per Bcql.g4's `caseInsensitive = true`."""
        tokens = lex(text)
        assert tokens[0].type == expected_type
        assert tokens[0].value == text


class TestLexerBrackets:
    def test_square_brackets(self):
        tokens = lex("[]")
        assert tokens[0].type == TokenType.LBRACKET
        assert tokens[1].type == TokenType.RBRACKET

    def test_parens(self):
        tokens = lex("()")
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.RPAREN

    def test_curly_brackets(self):
        tokens = lex("{}")
        assert tokens[0].type == TokenType.LBRACE
        assert tokens[1].type == TokenType.RBRACE


class TestLexerLookaround:
    def test_positive_lookahead(self):
        tokens = lex("(?=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKAHEAD_POS

    def test_negative_lookahead(self):
        tokens = lex("(?!")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKAHEAD_NEG

    def test_positive_lookbehind(self):
        tokens = lex("(?<=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKBEHIND_POS

    def test_negative_lookbehind(self):
        tokens = lex("(?<!")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LOOKBEHIND_NEG


class TestLexerXML:
    def test_lt(self):
        tokens = lex("<")
        assert tokens[0].type == TokenType.LT

    def test_lt_slash(self):
        tokens = lex("</")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LT_SLASH

    def test_gt(self):
        tokens = lex(">")
        assert tokens[0].type == TokenType.GT

    def test_slash_gt(self):
        tokens = lex("/>")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.SLASH_GT


class TestLexerArrows:
    def test_rel_arrow(self):
        tokens = lex("-obj->")
        assert tokens[0].type == TokenType.REL_LINE
        assert tokens[0].value == "-"

        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "obj"

        assert tokens[2].type == TokenType.REL_ARROW
        assert tokens[2].value == "->"

    def test_root_rel_arrow(self):
        tokens = lex("^-obj->")
        assert tokens[0].type == TokenType.ROOT_REL_CARET
        assert tokens[0].value == "^"

        assert tokens[1].type == TokenType.REL_LINE
        assert tokens[1].value == "-"

        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "obj"

        assert tokens[3].type == TokenType.REL_ARROW
        assert tokens[3].value == "->"

    def test_untyped_rel_arrow(self):
        tokens = lex("-->")
        assert tokens[0].type == TokenType.REL_LINE
        assert tokens[0].value == "-"

        assert tokens[1].type == TokenType.REL_ARROW
        assert tokens[1].value == "->"

    def test_untyped_root_rel_arrow(self):
        tokens = lex("^-->")
        assert tokens[0].type == TokenType.ROOT_REL_CARET
        assert tokens[0].value == "^"

        assert tokens[1].type == TokenType.REL_LINE
        assert tokens[1].value == "-"

        assert tokens[2].type == TokenType.REL_ARROW
        assert tokens[2].value == "->"

    def test_untyped_align_arrow(self):
        tokens = lex("==>nl")
        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[0].value == "="

        assert tokens[1].type == TokenType.ALIGN_ARROW
        assert tokens[1].value == "=>"

        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "nl"

    def test_untyped_optional_align_arrow(self):
        tokens = lex("==>nl?")
        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[0].value == "="

        assert tokens[1].type == TokenType.ALIGN_ARROW
        assert tokens[1].value == "=>"

        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "nl"

        assert tokens[3].type == TokenType.QUESTION
        assert tokens[3].value == "?"

    def test_align_arrow(self):
        tokens = lex("=word=>nl")

        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[0].value == "="

        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "word"

        assert tokens[2].type == TokenType.ALIGN_ARROW
        assert tokens[2].value == "=>"

        assert tokens[3].type == TokenType.IDENTIFIER
        assert tokens[3].value == "nl"


class TestLexerIntegers:
    def test_positive(self):
        tokens = lex("42")
        assert tokens[0].type == TokenType.INTEGER
        assert tokens[0].value == "42"

    def test_negative(self):
        tokens = lex("-5")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.INTEGER
        assert tokens[0].value == "-5"


class TestLexerOperators:
    def test_equals(self):
        tokens = lex("=")
        assert tokens[0].type == TokenType.EQ
        assert tokens[0].value == "="

    def test_not_equals(self):
        tokens = lex("!=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.NEQ
        assert tokens[0].value == "!="

    def test_less_than(self):
        tokens = lex("<")
        assert tokens[0].type == TokenType.LT
        assert tokens[0].value == "<"

    def test_less_equal(self):
        tokens = lex("<=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LTE
        assert tokens[0].value == "<="

    def test_greater_than(self):
        tokens = lex(">")
        assert tokens[0].type == TokenType.GT
        assert tokens[0].value == ">"

    def test_greater_equal(self):
        # Lexer tokenizes >= as two separate tokens: GT + EQ
        tokens = lex(">=")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.GTE
        assert tokens[0].value == ">="

    def test_bang(self):
        tokens = lex("!")
        assert tokens[0].type == TokenType.BANG

    def test_ampersand(self):
        tokens = lex("&")
        assert tokens[0].type == TokenType.AMP

    def test_pipe(self):
        tokens = lex("|")
        assert tokens[0].type == TokenType.PIPE

    def test_single_colon(self):
        tokens = lex(":")
        assert tokens[0].type == TokenType.COLON
        assert tokens[0].value == ":"

    def test_double_colon(self):
        tokens = lex("::")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.DOUBLE_COLON
        assert tokens[0].value == "::"

    def test_semicolon(self):
        tokens = lex(";")
        assert tokens[0].type == TokenType.SEMICOLON
        assert tokens[0].value == ";"

    def test_dot(self):
        tokens = lex(".")
        assert tokens[0].type == TokenType.DOT
        assert tokens[0].value == "."

    def test_comma(self):
        tokens = lex(",")
        assert tokens[0].type == TokenType.COMMA
        assert tokens[0].value == ","


class TestLexerComments:
    def test_single_comment_ignored(self):
        tokens = lex('"man" # this is a comment')
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "man"

    def test_multiline_comment_ignored(self):
        query = """"man" /* this is a
        multiline comment */"""
        tokens = lex(query)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "man"


class TestLexerPositions:
    def test_position_tracking(self):
        tokens = BCQLLexer('[word="man"]').tokenize()
        assert tokens[0].position == 0
        assert tokens[1].position == 1
        assert tokens[2].position == 5
        assert tokens[3].position == 6
        assert tokens[4].position == 11
        assert tokens[5].position == 12


class TestLexerErrors:
    def test_unclosed_string(self):
        with pytest.raises(BCQLSyntaxError):
            BCQLLexer('"unclosed').tokenize()

    def test_unexpected_dash(self):
        with pytest.raises(BCQLSyntaxError, match="Unexpected character '-'"):
            BCQLLexer("-").tokenize()

    def test_unexpected_caret_alone(self):
        with pytest.raises(BCQLSyntaxError, match="Unexpected character '\\^'"):
            BCQLLexer("^").tokenize()

    def test_unexpected_character(self):
        with pytest.raises(BCQLSyntaxError, match="Unexpected character"):
            BCQLLexer("@").tokenize()

    def test_root_parallel_relation_error(self):
        """'^' only starts '-' arrows, not '=' arrows, so '^==>' is an unexpected '^'."""
        with pytest.raises(BCQLSyntaxError, match="Unexpected character '\\^'"):
            BCQLLexer("^==>").tokenize()

    def test_unterminated_arrow(self):
        """'-foo' is not recognized as an arrow (no '->'), so '-' is unexpected."""
        with pytest.raises(BCQLSyntaxError, match="Unexpected character '-'"):
            BCQLLexer("-foo").tokenize()

    def test_unclosed_single_quote_string(self):
        with pytest.raises(BCQLSyntaxError):
            BCQLLexer("'unclosed").tokenize()

    def test_unclosed_literal_string(self):
        with pytest.raises(BCQLSyntaxError):
            BCQLLexer('l"unclosed').tokenize()


class TestLexerQuantifiers:
    def test_star(self):
        tokens = lex("*")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STAR
        assert tokens[0].value == "*"

    def test_plus(self):
        tokens = lex("+")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.PLUS
        assert tokens[0].value == "+"

    def test_question(self):
        tokens = lex("==>nl?")
        # The ? is emitted as part of alignment arrow handling
        assert tokens[-1].type == TokenType.QUESTION

    def test_question_standalone(self):
        tokens = lex('"word"?')
        assert tokens[0].type == TokenType.STRING
        assert tokens[1].type == TokenType.QUESTION
        assert tokens[1].value == "?"

    def test_repetition_braces(self):
        tokens = lex("{2,3}")
        assert tokens[0].type == TokenType.LBRACE
        assert tokens[1].type == TokenType.INTEGER
        assert tokens[1].value == "2"
        assert tokens[2].type == TokenType.COMMA
        assert tokens[3].type == TokenType.INTEGER
        assert tokens[3].value == "3"
        assert tokens[4].type == TokenType.RBRACE


class TestLexerSlash:
    def test_standalone_fwd_slash(self):
        tokens = lex("/")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.FWD_SLASH
        assert tokens[0].value == "/"

    def test_slash_gt_still_works(self):
        tokens = lex("/>")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.SLASH_GT

    def test_multiline_comment_still_works(self):
        tokens = lex('"a" /* comment */ "b"')
        assert len(tokens) == 2
        assert tokens[0].value == "a"
        assert tokens[1].value == "b"


class TestLexerArrowEdgeCases:
    def test_arrow_field_underscore(self):
        """Arrow with underscore field: -obj->_"""
        tokens = lex("-obj->_")
        assert tokens[0].type == TokenType.REL_LINE
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "obj"
        assert tokens[2].type == TokenType.REL_ARROW
        assert tokens[3].type == TokenType.UNDERSCORE
        assert tokens[3].value == "_"

    def test_alignment_arrow_field_underscore(self):
        """Alignment arrow with underscore field: =word=>_"""
        tokens = lex("=word=>_")
        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "word"
        assert tokens[2].type == TokenType.ALIGN_ARROW
        assert tokens[3].type == TokenType.UNDERSCORE

    def test_rel_arrow_with_field(self):
        """Relation arrow with target field: -dep->word"""
        tokens = lex("-dep->word")
        assert tokens[0].type == TokenType.REL_LINE
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "dep"
        assert tokens[2].type == TokenType.REL_ARROW
        assert tokens[3].type == TokenType.IDENTIFIER
        assert tokens[3].value == "word"

    def test_optional_alignment_field_underscore(self):
        """Alignment with optional underscore: ==>_?"""
        tokens = lex("==>_?")
        assert tokens[0].type == TokenType.ALIGN_LINE
        assert tokens[1].type == TokenType.ALIGN_ARROW
        assert tokens[2].type == TokenType.UNDERSCORE
        assert tokens[3].type == TokenType.QUESTION

    def test_standalone_rel_arrow(self):
        """Standalone `->` (e.g. implication in capture constraints)."""
        tokens = lex("->")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.REL_ARROW
        assert tokens[0].value == "->"

    def test_implication_in_context(self):
        """Implication `->` surrounded by other tokens as in capture constraints."""
        # Simplified version of: A.word = "the" -> B.pos = "noun"
        tokens = lex('A.word = "the" -> B.pos = "noun"')

        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "A"
        assert tokens[1].type == TokenType.DOT
        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "word"
        assert tokens[3].type == TokenType.EQ
        assert tokens[4].type == TokenType.STRING
        assert tokens[4].value == "the"
        assert tokens[5].type == TokenType.REL_ARROW
        assert tokens[6].type == TokenType.IDENTIFIER
        assert tokens[6].value == "B"
        assert tokens[7].type == TokenType.DOT
        assert tokens[8].type == TokenType.IDENTIFIER
        assert tokens[8].value == "pos"
        assert tokens[9].type == TokenType.EQ
        assert tokens[10].type == TokenType.STRING
        assert tokens[10].value == "noun"


class TestLexerWhitespace:
    def test_trailing_whitespace(self):
        tokens = lex('"a"  ')
        assert len(tokens) == 1
        assert tokens[0].value == "a"

    def test_only_whitespace(self):
        lexer = BCQLLexer("   ")
        result = lexer.tokenize()
        # Only whitespace produces no tokens (not even EOF from the else branch)
        # The while loop ends because _skip_whitespace moves _pos past len
        assert len(result) == 0

    def test_empty_source(self):
        lexer = BCQLLexer("")
        result = lexer.tokenize()
        # Empty string still produces an EOF token
        assert len(result) == 1
        assert result[0].type == TokenType.EOF


class TestLexerPropertiesAccess:
    def test_source_property(self):
        lexer = BCQLLexer("hello")
        assert lexer.source == "hello"

    def test_pos_property(self):
        lexer = BCQLLexer("hello")
        assert lexer.pos == 0


class TestLexerLiteralStringSingleQuote:
    def test_literal_single_quoted(self):
        tokens = lex("l'e.g.'")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.LITERAL_STRING
        assert tokens[0].value == "e.g."


class TestLexerTokenizeFunction:
    def test_tokenize_function(self):
        """Test the standalone tokenize() function."""
        result = tokenize('[word="man"]')
        assert isinstance(result, tuple)
        assert result[-1].type == TokenType.EOF
        assert len(result) == 6  # [ word = "man" ] EOF
