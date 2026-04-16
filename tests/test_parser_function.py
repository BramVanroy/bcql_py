"""Tests for function call parsing (Step 13): sequence-level query functions."""

import pytest
from conftest import parse, round_trip

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.models.capture import CaptureNode
from bcql_py.models.function import FunctionCallNode
from bcql_py.models.sequence import SequenceNode
from bcql_py.models.token import TokenQuery


class TestFunctionCallBasic:
    """Basic function call parsing: ``name(args)``."""

    def test_no_args(self):
        node = parse("myfunc()")
        assert isinstance(node, FunctionCallNode)
        assert node.name == "myfunc"
        assert node.args == []

    def test_single_query_arg(self):
        node = parse('rspan("cat")')
        assert isinstance(node, FunctionCallNode)
        assert node.name == "rspan"
        assert len(node.args) == 1
        assert isinstance(node.args[0], TokenQuery)

    def test_single_int_arg(self):
        node = parse("myfunc(3)")
        assert isinstance(node, FunctionCallNode)
        assert node.name == "myfunc"
        assert node.args == [3]

    def test_multiple_args_query_and_int(self):
        node = parse('fmeet("cat", 2)')
        assert isinstance(node, FunctionCallNode)
        assert node.name == "fmeet"
        assert len(node.args) == 2
        assert isinstance(node.args[0], TokenQuery)
        assert node.args[1] == 2

    def test_multiple_query_args(self):
        node = parse('meet([pos="N"], [pos="V"])')
        assert isinstance(node, FunctionCallNode)
        assert node.name == "meet"
        assert len(node.args) == 2
        assert all(isinstance(arg, TokenQuery) for arg in node.args)

    def test_multiple_int_args(self):
        node = parse("myfunc(1, 2, 3)")
        assert isinstance(node, FunctionCallNode)
        assert node.args == [1, 2, 3]

    def test_negative_int_arg(self):
        node = parse("myfunc(-5)")
        assert isinstance(node, FunctionCallNode)
        assert node.args == [-5]


class TestFunctionCallComplexArgs:
    """Function calls with complex sub-query arguments."""

    def test_sequence_arg(self):
        """A sequence as a function argument."""
        node = parse('rspan("the" "cat")')
        assert isinstance(node, FunctionCallNode)
        assert isinstance(node.args[0], SequenceNode)

    def test_token_query_arg(self):
        node = parse('rcapture([word="test"])')
        assert isinstance(node, FunctionCallNode)
        assert isinstance(node.args[0], TokenQuery)

    def test_mixed_args(self):
        """Multiple args mixing queries and integers."""
        node = parse('fmeet([word="cat"], [word="dog"], 3)')
        assert isinstance(node, FunctionCallNode)
        assert len(node.args) == 3
        assert isinstance(node.args[0], TokenQuery)
        assert isinstance(node.args[1], TokenQuery)
        assert node.args[2] == 3


class TestFunctionCallInContext:
    """Function calls as part of larger query structures."""

    def test_in_sequence(self):
        node = parse('"before" myfunc("x") "after"')
        assert isinstance(node, SequenceNode)
        assert len(node.children) == 3
        assert isinstance(node.children[1], FunctionCallNode)

    def test_with_capture_label(self):
        """``A:myfunc("cat")`` - captured function call."""
        node = parse('A:myfunc("cat")')
        assert isinstance(node, CaptureNode)
        assert node.label == "A"
        assert isinstance(node.body, FunctionCallNode)

    def test_parenthesized(self):
        """Function call inside parentheses."""
        from bcql_py.models.sequence import GroupNode

        node = parse('(myfunc("cat"))')
        assert isinstance(node, GroupNode)
        assert isinstance(node.child, FunctionCallNode)


class TestFunctionCallRoundTrip:
    """Round-trip tests for function calls."""

    def test_no_args_round_trip(self):
        round_trip("myfunc()")

    def test_single_query_round_trip(self):
        round_trip('rspan("cat")')

    def test_single_int_round_trip(self):
        round_trip("myfunc(3)")

    def test_multiple_args_round_trip(self):
        round_trip('meet([pos="N"], [pos="V"])')

    def test_mixed_args_round_trip(self):
        round_trip('fmeet("cat", 2)')

    def test_complex_query_arg_round_trip(self):
        round_trip('rspan("the" "cat")')

    def test_negative_int_round_trip(self):
        round_trip("myfunc(-5)")


class TestFunctionCallErrors:
    """Error cases for function call parsing."""

    def test_missing_closing_paren(self):
        with pytest.raises(BCQLSyntaxError, match="at end of function call"):
            parse('myfunc("cat"')

    def test_missing_opening_paren(self):
        """Bare IDENT without '(' is not a valid atom - handled by capture/span path."""
        with pytest.raises(BCQLSyntaxError):
            parse("myfunc")

    def test_trailing_comma(self):
        with pytest.raises(BCQLSyntaxError):
            parse('myfunc("cat",)')
