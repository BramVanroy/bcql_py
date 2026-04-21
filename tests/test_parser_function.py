"""Tests for function call parsing (Step 13): sequence-level query functions."""

import pytest
from conftest import round_trip_test

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models import RelationNode, UnderscoreNode
from bcql_py.models.capture import CaptureNode
from bcql_py.models.function import FunctionCallNode
from bcql_py.models.sequence import SequenceNode
from bcql_py.models.token import StringValue, TokenQuery
from bcql_py.parser import parse


class TestFunctionCallBasic:
    """Basic function call parsing: ``name(args)``."""

    def test_no_args(self):
        """``queryfunc()`` - a zero-argument query function call."""
        node = parse("queryfunc()")
        assert isinstance(node, FunctionCallNode)
        assert node.name == "queryfunc"
        assert node.args == []

    def test_single_query_arg(self):
        """``rspan("however")`` - compute the relation span for a lexical token query.

        The ``rspan`` function returns the span covered by a match in the dependency relations.
        The argument is a full query that is parsed as a sub-expression.
        """
        node = parse('rspan("however")')
        assert isinstance(node, FunctionCallNode)
        assert node.name == "rspan"
        assert len(node.args) == 1
        assert isinstance(node.args[0], TokenQuery)

    def test_single_int_arg(self):
        """``window(3)`` - a query function call with one numeric argument.

        Searches for: function-defined hits using a numeric parameter (e.g. a token window size).
        """
        node = parse("window(3)")
        assert isinstance(node, FunctionCallNode)
        assert node.name == "window"
        assert node.args == [3]

    def test_multiple_args_query_and_int(self):
        """``fmeet("however", 2)`` - function with a query argument and an integer window."""
        node = parse('fmeet("however", 2)')
        assert isinstance(node, FunctionCallNode)
        assert node.name == "fmeet"
        assert len(node.args) == 2
        assert isinstance(node.args[0], TokenQuery)
        assert node.args[1] == 2

    def test_multiple_query_args(self):
        """``meet([pos="N"], [pos="V"])`` - find positions where a noun and a verb co-occur.

        The ``meet`` function takes multiple query arguments and finds positions where
        all argument patterns are satisfied.
        """
        node = parse('meet([pos="N"], [pos="V"])')
        assert isinstance(node, FunctionCallNode)
        assert node.name == "meet"
        assert len(node.args) == 2
        assert all(isinstance(arg, TokenQuery) for arg in node.args)

    def test_multiple_int_args(self):
        """``window(1, 2, 3)`` - function call with three numeric parameters."""
        node = parse("window(1, 2, 3)")
        assert isinstance(node, FunctionCallNode)
        assert node.args == [1, 2, 3]

    def test_negative_int_arg(self):
        """``window(-5)`` - function call with a negative integer argument."""
        node = parse("window(-5)")
        assert isinstance(node, FunctionCallNode)
        assert node.args == [-5]


class TestFunctionCallComplexArgs:
    """Function calls with complex sub-query arguments."""

    def test_sequence_arg(self):
        """``rspan("New" "York")`` - function taking a multi-token query argument."""
        node = parse('rspan("New" "York")')
        assert isinstance(node, FunctionCallNode)
        assert isinstance(node.args[0], SequenceNode)

    def test_token_query_arg(self):
        """``rcapture([word="however"])`` - relation-capture function around a token query."""
        node = parse('rcapture([word="however"])')
        assert isinstance(node, FunctionCallNode)
        assert isinstance(node.args[0], TokenQuery)

    def test_mixed_args(self):
        """``fmeet([word="however"], [word="therefore"], 3)`` mixes two lexical queries with a window size."""
        node = parse('fmeet([word="however"], [word="therefore"], 3)')
        assert isinstance(node, FunctionCallNode)
        assert len(node.args) == 3
        assert isinstance(node.args[0], TokenQuery)
        assert isinstance(node.args[1], TokenQuery)
        assert node.args[2] == 3

    def test_single_arg_relation(self):
        """``rspan(_ -amod-> _)`` - function call with a complex query string as an argument."""
        node = parse("rspan(_ -amod-> _)")
        assert isinstance(node, FunctionCallNode)
        assert len(node.args) == 1
        assert isinstance(node.args[0], RelationNode)

    def test_multiple_args_embedded_rel_types(self):
        """``rspan(_ -nsubj-> (_ -amod-> _) ; -obj-> _, "all")``"""
        node = parse('rspan(_ -nsubj-> (_ -amod-> _) ; -obj-> _, "all")')
        assert isinstance(node, FunctionCallNode)
        assert len(node.args) == 2
        assert isinstance(node.args[0], RelationNode)
        assert isinstance(node.args[0].source, UnderscoreNode)
        assert len(node.args[0].children) == 2

        assert isinstance(node.args[1], TokenQuery)
        assert isinstance(node.args[1].shorthand, StringValue)
        assert node.args[1].shorthand.value == "all"


class TestFunctionCallInContext:
    """Function calls as part of larger query structures."""

    def test_in_sequence(self):
        """``"before" queryfunc("however") "after"`` embeds a function call in a sequence.

        Searches for: a three-part sequence where the middle element is a function query atom.
        """
        node = parse('"before" queryfunc("however") "after"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], FunctionCallNode)

    def test_with_capture_label(self):
        """``focus:queryfunc("however")`` applies a capture label to a function call."""
        node = parse('focus:queryfunc("however")')
        assert isinstance(node, CaptureNode)
        assert node.label == "focus"
        assert isinstance(node.body, FunctionCallNode)

    def test_parenthesized(self):
        """``(queryfunc("however"))`` - parenthesized function call as a grouped query atom."""
        from bcql_py.models.sequence import GroupNode

        node = parse('(queryfunc("however"))')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, FunctionCallNode)


class TestFunctionCallRoundTrip:
    """Round-trip tests for function calls."""

    def test_no_args_round_trip(self):
        """Round-trip: no-args function call preserves structure."""
        round_trip_test("queryfunc()")

    def test_single_query_round_trip(self):
        """Round-trip: single query arg preserves structure."""
        round_trip_test('rspan("however")')

    def test_single_int_round_trip(self):
        """Round-trip: single integer arg preserves structure."""
        round_trip_test("window(3)")

    def test_multiple_args_round_trip(self):
        """Round-trip: multiple query args preserve structure."""
        round_trip_test('meet([pos="N"], [pos="V"])')

    def test_mixed_args_round_trip(self):
        """Round-trip: mixed query and integer args preserve structure."""
        round_trip_test('fmeet("however", 2)')

    def test_complex_query_arg_round_trip(self):
        """Round-trip: sequence arg preserves structure."""
        round_trip_test('rspan("New" "York")')

    def test_negative_int_round_trip(self):
        """Round-trip: negative integer arg preserves structure."""
        round_trip_test("window(-5)")


class TestFunctionCallErrors:
    """Error cases for function call parsing."""

    def test_missing_closing_paren(self):
        """``queryfunc("however"`` - missing closing parenthesis after function arguments."""
        with pytest.raises(BCQLSyntaxError, match="at end of function call"):
            parse('queryfunc("however"')

    def test_missing_opening_paren(self):
        """``queryfunc`` - bare identifier without ``(`` is not a valid query atom."""
        with pytest.raises(BCQLSyntaxError):
            parse("queryfunc")

    def test_trailing_comma(self):
        """``queryfunc("however",)`` - trailing comma with no following argument."""
        with pytest.raises(BCQLSyntaxError):
            parse('queryfunc("however",)')
