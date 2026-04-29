"""Tests for the custom exception types.

Focus on the string-formatting contract: ``print(err)``, ``str(err)``,
``f"{err}"``, and ``"{}".format(err)`` must all produce the same human-readable
message (including the caret-annotated source line for syntax errors). This is
load-bearing for downstream consumers (LLM retry loops, CLI tools) that may use
either spelling.
"""

from __future__ import annotations

import io

import pytest

from bcql_py import (
    BCQLSyntaxError,
    BCQLValidationError,
    CorpusSpec,
    ValidationIssue,
    parse,
)


def _capture_print(value: object) -> str:
    """Return what ``print(value)`` would write to stdout (sans trailing newline)."""
    buf = io.StringIO()
    print(value, file=buf)
    return buf.getvalue().rstrip("\n")


class TestBCQLSyntaxErrorStringEquivalence:
    """``print(err)``, ``str(err)``, and f-string formatting must agree."""

    def test_print_matches_str_for_caught_error(self):
        with pytest.raises(BCQLSyntaxError) as excinfo:
            parse('[word="man"')
        err = excinfo.value
        assert _capture_print(err) == str(err)
        assert "^" in str(err)

    def test_fstring_matches_str(self):
        with pytest.raises(BCQLSyntaxError) as excinfo:
            parse('[word="man"')
        err = excinfo.value
        assert f"{err}" == str(err)
        assert "^" in str(err)

    def test_format_matches_str(self):
        with pytest.raises(BCQLSyntaxError) as excinfo:
            parse('[word="man"')
        err = excinfo.value
        assert "{}".format(err) == str(err)
        assert "^" in str(err)

    def test_str_includes_query_and_caret(self):
        with pytest.raises(BCQLSyntaxError) as excinfo:
            parse('[word="man"')
        text = str(err := excinfo.value)
        assert err.message in text
        assert err.query in text
        assert "^" in text
        # The caret line is the last line of the formatted message.
        lines = text.splitlines()
        assert lines[-1].lstrip().startswith("^")

    def test_print_includes_query_and_caret(self):
        """``print(err)`` alone (no ``str()``) must surface the caret line."""
        with pytest.raises(BCQLSyntaxError) as excinfo:
            parse("[pos=NOUN]")
        printed = _capture_print(excinfo.value)
        assert "[pos=NOUN]" in printed
        assert "^" in printed

    def test_constructed_without_position_omits_caret(self):
        """When no position/query is provided, the formatted text is just the message."""
        err = BCQLSyntaxError("bare message")
        assert str(err) == "bare message"
        assert _capture_print(err) == "bare message"
        assert f"{err}" == "bare message"

    def test_str_is_stable_across_calls(self):
        """``__str__`` must not depend on Exception side-effects (args mutation, etc.)."""
        err = BCQLSyntaxError(
            "some error", bcql_query='[word="x"', error_position=9
        )
        first = str(err)
        # Re-trigger via several entry points; all must produce the same output.
        assert str(err) == first
        assert f"{err}" == first
        assert _capture_print(err) == first
        assert "{!s}".format(err) == first


class TestValidationIssueStringEquivalence:
    """``ValidationIssue`` is a dataclass but defines ``__str__`` explicitly."""

    def test_print_matches_str_without_context(self):
        issue = ValidationIssue(
            kind="unknown_annotation",
            message="Unknown annotation 'foo'.",
            node_type="annotation_constraint",
        )
        assert _capture_print(issue) == str(issue)
        assert f"{issue}" == str(issue)
        assert "{}".format(issue) == str(issue)

    def test_print_matches_str_with_context(self):
        issue = ValidationIssue(
            kind="invalid_annotation_value",
            message="Value 'X' is not valid for closed attribute 'pos'.",
            node_type="annotation_constraint",
            context={"annotation": "pos", "value": "X"},
        )
        rendered = str(issue)
        assert _capture_print(issue) == rendered
        assert f"{issue}" == rendered
        # Context is included only in the string form, with key=repr(value) pairs.
        assert "annotation='pos'" in rendered
        assert "value='X'" in rendered
        assert rendered.startswith("[invalid_annotation_value]")


class TestBCQLValidationErrorStringEquivalence:
    """``BCQLValidationError`` aggregates issues; same string-equivalence rules apply."""

    def _build_single_issue_error(self) -> BCQLValidationError:
        spec = CorpusSpec(
            closed_attributes={"pos": frozenset({"NOUN", "VERB"})}
        )
        with pytest.raises(BCQLValidationError) as excinfo:
            parse('[pos="ADV"]', spec=spec)
        return excinfo.value

    def _build_multi_issue_error(self) -> BCQLValidationError:
        spec = CorpusSpec(
            open_attributes={"word"},
            closed_attributes={"pos": frozenset({"NOUN", "VERB"})},
            strict_attributes=True,
            allow_alignment=False,
        )
        with pytest.raises(BCQLValidationError) as excinfo:
            parse(
                '[pos="ADV" & morph="Plur"] "x" ==>nl "y"',
                spec=spec,
                fail_fast=False,
            )
        return excinfo.value

    def test_single_issue_print_matches_str(self):
        err = self._build_single_issue_error()
        assert _capture_print(err) == str(err)
        assert f"{err}" == str(err)
        assert "{}".format(err) == str(err)

    def test_single_issue_message_matches_issue_str(self):
        """With one issue, the error's string form is exactly that issue's string form."""
        err = self._build_single_issue_error()
        assert len(err.issues) == 1
        assert str(err) == str(err.issues[0])

    def test_multi_issue_print_matches_str(self):
        err = self._build_multi_issue_error()
        assert _capture_print(err) == str(err)
        assert f"{err}" == str(err)

    def test_multi_issue_lists_every_issue(self):
        err = self._build_multi_issue_error()
        rendered = str(err)
        assert rendered.startswith(f"{len(err.issues)} validation issue(s):")
        for issue in err.issues:
            assert str(issue) in rendered

    def test_empty_issue_list_rejected(self):
        with pytest.raises(ValueError):
            BCQLValidationError([])


class TestStrConcatenationRequiresExplicitStr:
    """The one place where ``str(err)`` is genuinely required: ``+`` concatenation."""

    def test_plus_concatenation_with_exception_raises(self):
        err = BCQLSyntaxError("oops", bcql_query="[", error_position=0)
        with pytest.raises(TypeError):
            "prefix: " + err  # type: ignore[operator]

    def test_plus_concatenation_with_str_works(self):
        err = BCQLSyntaxError("oops", bcql_query="[", error_position=0)
        combined = "prefix: " + str(err)
        assert combined.startswith("prefix: ")
        assert str(err) in combined

    def test_fstring_does_not_require_explicit_str(self):
        """f-strings invoke ``__str__`` automatically, so explicit ``str()`` is redundant."""
        err = BCQLSyntaxError("oops", bcql_query="[", error_position=0)
        assert f"{err}" == f"{str(err)}"
