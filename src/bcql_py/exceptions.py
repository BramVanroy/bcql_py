from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


__all__ = ["BCQLSyntaxError", "BCQLValidationError", "ValidationIssue"]


class BCQLSyntaxError(Exception):
    def __init__(self, error_message: str, *, bcql_query: str = "", error_position: int | None = None) -> None:
        self.query = bcql_query
        self.position = error_position
        self.message = error_message
        super().__init__(str(self))

    def __str__(self) -> str:
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


@dataclass(frozen=True)
class ValidationIssue:
    """A single semantic validation problem found during :func:`bcql_py.validate`.
    In practice, there may be multiple issues collected in a :class:`BCQLValidationError`
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
        if self.context:
            ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"[{self.kind}] {self.message} ({ctx})"
        return f"[{self.kind}] {self.message}"


class BCQLValidationError(Exception):
    """Raised when an AST does not satisfy a :class:`CorpusSpec`.

    Collects one or more :class:`ValidationIssue` instances so that callers can surface
    every problem at once (when ``fail_fast=False``) or just the first (default).

    Attributes:
        issues: One or more :class:`ValidationIssue` entries describing what went wrong.
    """

    def __init__(self, issues: list[ValidationIssue]) -> None:
        if not issues:
            raise ValueError("BCQLValidationError requires at least one issue.")
        self.issues = issues
        super().__init__(str(self))

    def __str__(self) -> str:
        if len(self.issues) == 1:
            return str(self.issues[0])
        lines = [f"{len(self.issues)} validation issue(s):"]
        lines.extend(f"  - {issue}" for issue in self.issues)
        return "\n".join(lines)
