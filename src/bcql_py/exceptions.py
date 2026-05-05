"""Custom exceptions and validation issue types for bcql_py."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


__all__ = ["BCQLSyntaxError", "BCQLValidationError", "ValidationIssue"]


class BCQLSyntaxError(Exception):
    """A syntax error with optional source and position, raised when tokenization or parsing of a BCQL query fails.

    Attributes:
        error_message: Human-readable parse or lexing error message.
        bcql_query: Original BCQL source query.
        error_position: 0-based character position in ``bcql_query``.
    """

    def __init__(
        self,
        error_message: str,
        *,
        bcql_query: str = "",
        error_position: int | None = None,
    ) -> None:
        self.query = bcql_query
        self.position = error_position
        self.message = error_message
        super().__init__(str(self))

    def __str__(self) -> str:
        """Return a readable message including a caret position when available."""
        # Potential issue: this assumes there are no newlines in the query
        # TODO: check that bcql cannot/should not contain newlines which might mess with this error formatting
        parts = [self.message]
        if self.query and self.position is not None:
            parts.append(f"  {self.query}")
            parts.append(f"  {' ' * self.position}^")
        return "\n".join(parts)


IssueKind = Literal[
    "unknown_annotation",
    "invalid_annotation_value",
    "unknown_span_tag",
    "unknown_span_attribute",
    "invalid_span_attribute_value",
    "alignment_not_allowed",
    "unknown_alignment_field",
    "relations_not_allowed",
    "unknown_relation_type",
]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single semantic validation problem found during [validate()][bcql_py.validate].
    In practice, there may be multiple issues collected in a [BCQLValidationError][bcql_py.exceptions.BCQLValidationError]
    to report them all at once instead of just the first one.

    Attributes:
        kind: A short machine-readable label identifying the issue category.
        message: Human-readable description of the problem.
        node_type: The ``node_type`` discriminator of the offending AST node.
        context: Extra context (e.g. the offending annotation name, value, or tag).
    """

    kind: IssueKind
    message: str
    node_type: str
    context: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return this issue as a compact single-line message."""
        if self.context:
            ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"[{self.kind}] {self.message} ({ctx})"
        return f"[{self.kind}] {self.message}"


class BCQLValidationError(Exception):
    """Raised when an AST does not satisfy a [CorpusSpec][bcql_py.validation.CorpusSpec].

    Collects one or more [ValidationIssue][bcql_py.exceptions.ValidationIssue] instances so that callers can surface
    every problem at once (when ``fail_fast=False``) or just the first (default).

    Attributes:
        issues: One or more [ValidationIssue][bcql_py.exceptions.ValidationIssue] entries describing what went wrong.
    """

    def __init__(self, issues: list[ValidationIssue]) -> None:
        if not issues:
            raise ValueError(
                "BCQLValidationError requires at least one issue."
            )
        self.issues = issues
        super().__init__(str(self))

    def __str__(self) -> str:
        """Return one issue or a multi-line list of all validation issues as a string."""
        if len(self.issues) == 1:
            return str(self.issues[0])
        lines = [f"{len(self.issues)} validation issue(s):"]
        lines.extend(f"  - {issue}" for issue in self.issues)
        return "\n".join(lines)
