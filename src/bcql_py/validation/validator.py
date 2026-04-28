"""So-called Visitor that walks a BCQL AST and checks it against a :class:`CorpusSpec`.

The traversal uses Pydantic's ``model_fields`` introspection to recurse into any
field whose value is a :class:`~bcql_py.models.base.BCQLNode`, including nested
lists and dict values (used by :class:`~bcql_py.models.span.SpanQuery` for
attributes).

TODO: only literal string values are checked against closed attribute sets; regex
values are skipped for now.
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any, Iterable, Iterator

from bcql_py.exceptions import BCQLValidationError, ValidationIssue
from bcql_py.models.alignment import AlignmentNode, AlignmentOperator
from bcql_py.models.base import BCQLNode
from bcql_py.models.relation import (
    ChildConstraint,
    RelationOperator,
    RootRelationNode,
)
from bcql_py.models.span import SpanQuery
from bcql_py.models.token import (
    AnnotationConstraint,
    IntegerRangeConstraint,
    StringValue,
)
from bcql_py.validation.spec import CorpusSpec


__all__ = ["validate"]


class _StopValidation(Exception):
    """Internal signal to abort the traversal in fail-fast mode."""


class _Validator:
    """Depth-first AST walker that accumulates :class:`ValidationIssue` objects.

    Not part of the public API: callers should go through :func:`validate`. The
    class only holds per-run state (the spec, the fail-fast flag, and the list
    of issues found so far) so the traversal can stay method-based.

    Encountered issues are saved to :attr:`issues` as they are found. In
    fail-fast mode, the first issue also triggers a :class:`_StopValidation` exception
    to immediately stop the run, so that :func:`validate` can report the first issue found.
    """

    def __init__(self, spec: CorpusSpec, *, fail_fast: bool):
        """Initialize a fresh validator run.

        Args:
            spec: The :class:`CorpusSpec` to validate against.
            fail_fast: If ``True``, stop at the first issue; otherwise collect
                every issue encountered during the walk.
        """
        self.spec = spec
        self.fail_fast = fail_fast
        self.issues: list[ValidationIssue] = []

    def run(self, root: BCQLNode):
        """Walk *root* and populate :attr:`issues`.

        In fail-fast mode, :meth:`_record` raises :class:`_StopValidation` on the
        first issue; this method catches it so the traversal unwinds cleanly and
        :func:`validate` can inspect :attr:`issues` afterward. In collect-all
        mode, the walk runs to completion.

        Args:
            root: The AST root node to validate.
        """
        try:
            self._visit(root)
        except _StopValidation:
            return

    def _record(self, issue: ValidationIssue):
        """Append *issue* to :attr:`issues` and abort the walk if fail-fast is on.

        Raises:
            _StopValidation: When ``fail_fast`` is ``True``, to unwind the
                recursive traversal back up to :meth:`run`.
        """
        self.issues.append(issue)
        if self.fail_fast:
            raise _StopValidation

    def _visit(self, node: BCQLNode):
        """Validate ``node`` and recurse into every child node it owns."""
        self._check(node)
        for child in _iter_child_nodes(node):
            self._visit(child)

    def _check(self, node: BCQLNode):
        """Dispatch ``node`` to the type-specific checker, if any.

        Nodes with no semantic constraints on this spec are silently skipped.
        """
        if isinstance(node, AnnotationConstraint):
            self._check_annotation(node)
        elif isinstance(node, IntegerRangeConstraint):
            self._check_integer_range(node)
        elif isinstance(node, SpanQuery):
            self._check_span(node)
        elif isinstance(node, RelationOperator) or isinstance(
            node, RootRelationNode
        ):
            self._check_relation_operator(node)
        elif isinstance(node, ChildConstraint):
            pass
        elif isinstance(node, AlignmentOperator):
            self._check_alignment_operator(node)
        elif isinstance(node, AlignmentNode):
            self._check_alignment(node)

    def _check_annotation(self, node: AnnotationConstraint):
        """Validate an ``[annotation="value"]`` constraint.

        Records ``unknown_annotation`` when ``strict_attributes`` is set and the
        annotation is not listed on the spec, and ``invalid_annotation_value``
        when the annotation is closed-class and the (literal) value is not in
        its allowed set. Regex values are skipped: see :func:`_is_literal_value`.
        """
        name = node.annotation
        # Attribute given but not present in the spec: always an error in strict mode
        if self.spec.strict_attributes and not self.spec.has_annotation(name):
            self._record(
                ValidationIssue(
                    kind="unknown_annotation",
                    message=f"Unknown annotation {name!r}.",
                    node_type=node.node_type,
                    context={"annotation": name},
                )
            )
            return
        # Consider valid (return) if the attribute name is not part of any closed-class set
        allowed = self.spec.closed_attributes.get(name)
        if allowed is None:
            return

        # If this is a closed-class attribute, check the value
        value = node.value
        # TODO: we are only checking literal values and not yet try to validate regex patterns
        # Regex patterns are skipped (and thus allowed)
        if _is_literal_value(value) and value.value not in allowed:
            suggestion = _suggest(value.value, allowed)
            base = f"Value {value.value!r} is not valid for closed attribute {name!r}."
            self._record(
                ValidationIssue(
                    kind="invalid_annotation_value",
                    message=base + _format_hint(suggestion, allowed),
                    node_type=node.node_type,
                    context={
                        "annotation": name,
                        "value": value.value,
                        "suggestion": suggestion,
                        "allowed": sorted(allowed),
                    },
                )
            )

    def _check_integer_range(self, node: IntegerRangeConstraint):
        """Validate an integer-range constraint (e.g. ``pos_confidence=in[50,100]``).

        Only the annotation name is checked here (against ``strict_attributes``).
        """
        name = node.annotation
        # Attribute given but not present in the spec: always an error in strict mode
        if self.spec.strict_attributes and not self.spec.has_annotation(name):
            self._record(
                ValidationIssue(
                    kind="unknown_annotation",
                    message=f"Unknown annotation {name!r}.",
                    node_type=node.node_type,
                    context={"annotation": name},
                )
            )

    def _check_span(self, node: SpanQuery):
        """Validate an XML span query (e.g. ``<s/>``, ``<ne type="PER"/>``).

        Records ``unknown_span_tag`` when ``allowed_span_tags`` is set and the
        tag is not listed, and ``unknown_span_attribute`` for each XML attribute
        not allowed for this tag under ``allowed_span_attributes``. A tag with
        no per-tag entry in ``allowed_span_attributes`` is unconstrained.
        """
        # Tag name can be a string or StringValue. If it is a StringValue,
        # we skip validation since it may be a regex pattern rather than a literal tag name.
        tag_name = node.tag_name if isinstance(node.tag_name, str) else None
        if self.spec.allowed_span_tags is not None and tag_name is not None:
            if tag_name not in self.spec.allowed_span_tags:
                self._record(
                    ValidationIssue(
                        kind="unknown_span_tag",
                        message=f"Unknown span tag {tag_name!r}.",
                        node_type=node.node_type,
                        context={"tag": tag_name},
                    )
                )
                return
        # If no strict checks for span attributes or no tag name, skip attribute checks
        if self.spec.allowed_span_attributes is None or tag_name is None:
            return

        # Allowed_span_attributes specifies for a given tag which attributes are allowed
        # Consider valid (return) if the tag name is not given (since no attrs specified)
        tag_attrs = self.spec.allowed_span_attributes.get(tag_name)
        if tag_attrs is None:
            return
        for attr_name in node.attributes:
            if attr_name not in tag_attrs:
                self._record(
                    ValidationIssue(
                        kind="unknown_span_attribute",
                        message=f"Unknown XML attribute {attr_name!r} for span {tag_name!r}.",
                        node_type=node.node_type,
                        context={"tag": tag_name, "attribute": attr_name},
                    )
                )

    def _check_relation_operator(
        self, node: RelationOperator | RootRelationNode
    ):
        """Validate a dependency relation operator (``-type->`` between tokens)
        or a root relation (``^-->`` from the root).

        Records ``relations_not_allowed`` when the spec forbids relations, and
        otherwise delegates name checking to :meth:`_check_relation_type`.
        """
        if not self.spec.allow_relations:
            self._record(
                ValidationIssue(
                    kind="relations_not_allowed",
                    message="Dependency relations are not allowed by this corpus spec.",
                    node_type=node.node_type,
                )
            )
            return
        self._check_relation_type(node.relation_type, node.node_type)

    def _check_relation_type(self, relation_type: str | None, node_type: str):
        """Check a relation type name against ``spec.allowed_relations``.

        No-ops when the node has no named relation or the spec places no
        restriction on relation names. Regex-shaped names (e.g. ``nsubj.*``)
        are skipped to avoid false positives; only literal names are checked.

        Args:
            relation_type: The literal relation name from the AST, or ``None``.
            node_type: The originating node's ``node_type`` discriminator,
                attached to any issue produced for source-locating feedback.
        """
        if relation_type is None or self.spec.allowed_relations is None:
            return
        if _looks_like_regex(relation_type):
            return
        allowed = self.spec.allowed_relations
        if relation_type not in allowed:
            suggestion = _suggest(relation_type, allowed)
            base = f"Unknown relation type {relation_type!r}."
            self._record(
                ValidationIssue(
                    kind="unknown_relation_type",
                    message=base + _format_hint(suggestion, allowed),
                    node_type=node_type,
                    context={
                        "relation": relation_type,
                        "suggestion": suggestion,
                        "allowed": sorted(allowed),
                    },
                )
            )

    def _check_alignment_operator(self, node: AlignmentOperator):
        """Validate the ``==>`` operator and its target field.

        Records ``alignment_not_allowed`` when the spec forbids alignment, and
        ``unknown_alignment_field`` when the target field is not in
        ``allowed_alignment_fields`` (if that set is constrained).
        """
        if not self.spec.allow_alignment:
            self._record(
                ValidationIssue(
                    kind="alignment_not_allowed",
                    message="Alignment (==>) is not allowed by this corpus spec.",
                    node_type=node.node_type,
                )
            )
            return
        if (
            self.spec.allowed_alignment_fields is not None
            and node.target_field not in self.spec.allowed_alignment_fields
        ):
            allowed = self.spec.allowed_alignment_fields
            suggestion = _suggest(node.target_field, allowed)
            base = f"Unknown alignment target field {node.target_field!r}."
            self._record(
                ValidationIssue(
                    kind="unknown_alignment_field",
                    message=base + _format_hint(suggestion, allowed),
                    node_type=node.node_type,
                    context={
                        "field": node.target_field,
                        "suggestion": suggestion,
                        "allowed": sorted(allowed),
                    },
                )
            )

    def _check_alignment(self, node: AlignmentNode):
        """Validate a full alignment node; records ``alignment_not_allowed`` if forbidden.

        The per-operator field check is handled by
        :meth:`_check_alignment_operator` as the walk descends into the node's
        operator child, so this method only enforces the top-level toggle.
        """
        if not self.spec.allow_alignment:
            self._record(
                ValidationIssue(
                    kind="alignment_not_allowed",
                    message="Alignment (==>) is not allowed by this corpus spec.",
                    node_type=node.node_type,
                )
            )


def _iter_child_nodes(node: BCQLNode) -> Iterator[BCQLNode]:
    """Yield every :class:`BCQLNode` reachable as a direct child of ``node``.

    Walks only into typed fields of the Pydantic model, so we don't traverse
    into unrelated containers. Lists and dict values are expanded element-wise.
    """
    for field_name in type(node).model_fields:
        value = getattr(node, field_name)
        yield from _walk(value)


def _walk(value: Any) -> Iterator[BCQLNode]:
    """Recursively yield every :class:`BCQLNode` reachable inside *value*.

    Descends into lists, tuples, and dict values (dict keys are ignored since
    AST container keys are plain strings). Non-node leaves produce nothing.
    """
    if isinstance(value, BCQLNode):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)


def _is_literal_value(value: StringValue) -> bool:
    """Treat a StringValue as a literal iff it has the ``l`` prefix OR contains
    no regex-significant metacharacters.

    BCQL values are regex by default; ``l"..."`` forces literal. We only validate
    values we are confident are literal so that e.g. ``pos="NOUN|VERB"`` is not
    falsely reported as invalid. Users who want stricter checks can pre-process
    their queries or pass literal values.
    """
    if value.is_literal:
        return True
    return not _looks_like_regex(value.value)


_REGEX_METACHARS = frozenset(".^$*+?()[]{}|\\")


def _suggest(value: str, allowed: Iterable[str]) -> str | None:
    """Return the single closest match for *value* in *allowed*, or ``None``.

    Uses :func:`difflib.get_close_matches` (Ratcliff-Obershelp similarity) with a
    fixed cutoff so only a plausibly-meant-this-one entry is returned. Closed
    sets in typical corpus specs are small (tens of tags), so stdlib is fast
    enough; no external edit-distance dependency is required.
    """
    matches = get_close_matches(value, list(allowed), n=1, cutoff=0.6)
    return matches[0] if matches else None


def _format_hint(suggestion: str | None, allowed: Iterable[str]) -> str:
    """Format the trailing portion of a validation message with suggestion and allowed values.

    Produces a leading-space prefixed string so callers can concatenate it to a
    base message.

    Args:
        suggestion: Closest match already computed by :func:`_suggest`, or ``None``.
        allowed: The full set of allowed values for the constraint.

    Returns:
        A string beginning with a single space, e.g. ``" Did you mean 'NOUN'?
        Allowed values: ADJ, ADP, ..."``, or ``""`` if *allowed* is empty.
    """
    allowed_sorted = sorted(allowed)
    if not allowed_sorted:
        return ""
    parts: list[str] = []
    if suggestion is not None:
        parts.append(f"Did you mean {suggestion!r}?")
    parts.append(f"Allowed values: {', '.join(allowed_sorted)}.")
    return " " + " ".join(parts)


def _looks_like_regex(text: str) -> bool:
    """Return ``True`` when *text* contains any regex-significant metacharacter.

    A cheap syntactic test used to avoid false-positive validation errors on
    values that are probably patterns rather than literals.
    """
    return any(ch in _REGEX_METACHARS for ch in text)


def validate(ast: BCQLNode, spec: CorpusSpec, *, fail_fast: bool = True):
    """Validate a parsed BCQL AST against *spec*, raising on any issue.

    Args:
        ast: The root :class:`~bcql_py.models.base.BCQLNode` returned by
            :func:`bcql_py.parse`.
        spec: The :class:`CorpusSpec` describing what the corpus allows.
        fail_fast: When ``True`` (default), raise as soon as the first issue is
            found. When ``False``, collect every issue and raise once at the end
            so callers can report them all together.

    Raises:
        BCQLValidationError: If one or more validation issues are found. The
            raised exception's ``issues`` attribute holds the full list.

    Example::

        >>> from bcql_py import CorpusSpec, parse, validate
        >>> spec = CorpusSpec(
        ...     open_attributes={"word"},
        ...     closed_attributes={"pos": {"NOUN", "VERB"}},
        ... )
        >>> validate(parse('[pos="NOUN"]'), spec)  # passes silently
        >>> try:
        ...     validate(parse('[pos="ADJ"]'), spec)
        ... except Exception as exc:
        ...     print(exc.issues[0].kind)
        invalid_annotation_value
    """
    validator = _Validator(spec, fail_fast=fail_fast)
    validator.run(ast)
    if validator.issues:
        raise BCQLValidationError(validator.issues)
