"""Corpus-specific semantic specification used by :func:`bcql_py.validation.validate`.

A :class:`CorpusSpec` describes the surface vocabulary of a particular corpus:
which annotations exist, which annotations are closed-class (with a fixed set of
allowed values), which XML span tags and attributes are available, and whether
alignment or dependency-relation queries are allowed at all. This is a semantic
layer that can be used on top of the "syntactic" AST structure to validate
a query against corpus-specific constraints.

The spec is a frozen Pydantic model; use :meth:`CorpusSpec.extend` or :meth:`CorpusSpec.merge` to
compose specs (e.g. to add your own corpus on top of a preset).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


__all__ = ["CorpusSpec"]


class CorpusSpec(BaseModel):
    """Immutable description of a corpus' semantic vocabulary.

    All fields default to the most permissive setting ("anything goes") so that a
    bare ``CorpusSpec()`` is a no-op validator. Narrow the spec by listing the
    annotations, tags, and relations your corpus actually supports.

    Attributes:
        open_attributes: Annotation names whose value space is unconstrained
            (e.g. ``word``, ``lemma``).
        closed_attributes: Annotation names whose values are restricted to a
            fixed set (e.g. ``pos`` -> ``{"NOUN", "VERB", ...}``).
        strict_attributes: When ``True``, any annotation not listed in
            ``open_attributes`` or ``closed_attributes`` is an error. When
            ``False`` (default), unknown annotations are accepted.
        allowed_span_tags: Allowed XML span tag names (e.g. ``s``, ``p``, ``ne``),
            or ``None`` to allow any tag.
        allowed_span_attributes: Per-tag allowed XML attribute values. Missing
            tags default to no constraint. Use ``None`` to allow any attribute.
        allow_alignment: If ``False``, any use of the alignment (``==>``) operator
            raises a validation error.
        allowed_alignment_fields: Allowed target field names for alignment
            queries, or ``None`` to allow any.
        allow_relations: If ``False``, any relation operator (``-type->`` or
            ``^-type->``) raises a validation error.
        allowed_relations: Allowed relation type names, or ``None`` to allow
            any. An empty set means "no named relations allowed" (use
            ``allow_relations=False`` for that instead).

    Example::

        >>> spec = CorpusSpec(open_attributes={"word"}, closed_attributes={"pos": {"NOUN", "VERB"}})
        >>> "pos" in spec.closed_attributes
        True
        >>> sorted(spec.closed_attributes["pos"])
        ['NOUN', 'VERB']
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=False)

    open_attributes: frozenset[str] = Field(
        default_factory=frozenset,
        description="Annotation names that can have any value",
    )
    closed_attributes: dict[str, frozenset[str]] = Field(
        default_factory=dict,
        description="Per-attribute allowed values for closed-class annotations",
    )
    strict_attributes: bool = Field(
        default=False,
        description="Is the spec 'strict', that means, are annotations not listed in either open_attributes or closed_attributes disallowed?",
    )
    allowed_span_tags: frozenset[str] | None = Field(
        default=None,
        description="Allowed XML span tag names, or None to allow any",
    )
    allowed_span_attributes: dict[str, frozenset[str]] | None = Field(
        default=None,
        description="Per-tag allowed XML attribute names, or None to allow any",
    )
    allow_alignment: bool = Field(
        default=True,
        description="Is alignment (==>) allowed?",
    )
    allowed_alignment_fields: frozenset[str] | None = Field(
        default=None,
        description="Allowed target field names for alignment, or None to allow any",
    )
    allow_relations: bool = Field(
        default=True,
        description="Are dependency relations (--> or ^-->) allowed?",
    )
    allowed_relations: frozenset[str] | None = Field(
        default=None,
        description="Allowed relation type names, or None to allow any",
    )

    @field_validator("closed_attributes", mode="before")
    @classmethod
    def _coerce_closed_attributes(cls, value: Any) -> Any:
        """Normalize raw input into ``dict[str, frozenset[str]]`` before Pydantic validation.

        Runs in ``mode="before"`` so callers can pass convenient shapes (e.g. a
        ``dict`` whose values are lists or sets) and still end up with the frozen,
        hashable inner sets the field declares.

        Args:
            value: The raw input for ``closed_attributes`` (any type).

        Returns:
            ``{}`` if *value* is ``None``; a dict with string keys and
            ``frozenset`` values if *value* is a mapping; otherwise *value*
            unchanged (to let Pydantic raise a normal validation error).
        """
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return {str(k): frozenset(v) for k, v in value.items()}
        return value

    @field_validator("allowed_span_attributes", mode="before")
    @classmethod
    def _coerce_span_attributes(cls, value: Any) -> Any:
        """Normalize raw input into ``dict[str, frozenset[str]] | None`` before Pydantic validation.

        Args:
            value: The raw input for ``allowed_span_attributes`` (any type).

        Returns:
            ``None`` if *value* is ``None``; a dict with string keys and
            ``frozenset`` values if *value* is a mapping; otherwise *value*
            unchanged (to let Pydantic raise a normal validation error).
        """
        if value is None:
            return None
        if isinstance(value, Mapping):
            return {str(k): frozenset(v) for k, v in value.items()}
        return value

    def extend(
        self,
        *,
        open_attributes: Iterable[str] | None = None,
        closed_attributes: Mapping[str, Iterable[str]] | None = None,
        allowed_span_tags: Iterable[str] | None = None,
        allowed_span_attributes: Mapping[str, Iterable[str]] | None = None,
        allowed_alignment_fields: Iterable[str] | None = None,
        allowed_relations: Iterable[str] | None = None,
        strict_attributes: bool | None = None,
        allow_alignment: bool | None = None,
        allow_relations: bool | None = None,
    ) -> CorpusSpec:
        """Return a new spec with the given additions/overrides merged in.
        Similar to :meth:`merge`, but with a more granular API that allows adding
        specific entries without having to construct a full spec.

        Args:
            open_attributes: Extra open-class annotation names to union in.
            closed_attributes: Extra closed-class attributes; per-key values union.
            allowed_span_tags: Extra allowed span tag names.
            allowed_span_attributes: Extra per-tag attribute names.
            allowed_alignment_fields: Extra alignment target fields.
            allowed_relations: Extra relation type names.
            strict_attributes: Override the strict-attributes flag.
            allow_alignment: Override the alignment allowed flag.
            allow_relations: Override the relations allowed flag.

        Returns:
            A new :class:`CorpusSpec`; the receiver is not modified.

        Example::

            >>> base = CorpusSpec(open_attributes={"word"})
            >>> extended = base.extend(open_attributes={"lemma"})
            >>> sorted(extended.open_attributes)
            ['lemma', 'word']
        """
        updates: dict[str, Any] = {}
        if open_attributes is not None:
            updates["open_attributes"] = self.open_attributes | frozenset(
                open_attributes
            )
        if closed_attributes is not None:
            merged = dict(self.closed_attributes)
            for key, values in closed_attributes.items():
                merged[key] = merged.get(key, frozenset()) | frozenset(values)
            updates["closed_attributes"] = merged
        if allowed_span_tags is not None:
            base_tags = self.allowed_span_tags or frozenset()
            updates["allowed_span_tags"] = base_tags | frozenset(
                allowed_span_tags
            )
        if allowed_span_attributes is not None:
            merged_attrs = dict(self.allowed_span_attributes or {})
            for key, values in allowed_span_attributes.items():
                merged_attrs[key] = merged_attrs.get(
                    key, frozenset()
                ) | frozenset(values)
            updates["allowed_span_attributes"] = merged_attrs
        if allowed_alignment_fields is not None:
            base_fields = self.allowed_alignment_fields or frozenset()
            updates["allowed_alignment_fields"] = base_fields | frozenset(
                allowed_alignment_fields
            )
        if allowed_relations is not None:
            base_rels = self.allowed_relations or frozenset()
            updates["allowed_relations"] = base_rels | frozenset(
                allowed_relations
            )
        if strict_attributes is not None:
            updates["strict_attributes"] = strict_attributes
        if allow_alignment is not None:
            updates["allow_alignment"] = allow_alignment
        if allow_relations is not None:
            updates["allow_relations"] = allow_relations
        return self.model_copy(update=updates)

    def merge(self, other: CorpusSpec) -> CorpusSpec:
        """Return a new spec combining this spec with *other*.
        In case of conflict, *other* wins (except for boolean flags, see below).

        Set-valued fields are unioned. For the nullable set-valued fields
        (``allowed_span_tags``, ``allowed_alignment_fields``, ``allowed_relations``,
        and the dict-shaped ``allowed_span_attributes``), ``None`` means "no
        constraint". A concrete set/dict is treated as *more restrictive* than
        ``None``, so when one side is ``None`` and the other lists entries, the
        result is the listed entries: ``None`` survives only when both sides are
        ``None``. This mirrors the boolean rule below: a concrete restriction
        always beats "no constraint".

        WARNING: For boolean flags, ``other`` wins only when it is more restrictive
        (``False`` beats ``True``) so that merging in a preset cannot silently
        re-enable something the caller disabled.

        Args:
            other: Another spec to merge into this one.

        Returns:
            A new :class:`CorpusSpec` representing the union.

        Example::

            >>> spec1 = CorpusSpec(open_attributes={"word"}, allow_alignment=True)
            >>> spec2 = CorpusSpec(open_attributes={"lemma"}, closed_attributes={"pos": {"NOUN", "VERB"}}, allow_alignment=False)
            >>> merged = spec1.merge(spec2)
            >>> sorted(merged.open_attributes)
            ['lemma', 'word']
            >>> "pos" in merged.closed_attributes
            True
            >>> merged.allow_alignment
            False
        """

        def _union_optional(
            a: frozenset[str] | None, b: frozenset[str] | None
        ) -> frozenset[str] | None:
            """Union two ``frozenset[str] | None`` fields under "restriction beats None".

            Used for the nullable frozenset fields only (``allowed_span_tags``,
            ``allowed_alignment_fields``, ``allowed_relations``).
            """
            if a is None and b is None:
                return None
            return (a or frozenset()) | (b or frozenset())

        merged_closed: dict[str, frozenset[str]] = dict(self.closed_attributes)
        for key, values in other.closed_attributes.items():
            merged_closed[key] = merged_closed.get(key, frozenset()) | values

        if (
            self.allowed_span_attributes is None
            and other.allowed_span_attributes is None
        ):
            merged_span_attrs: dict[str, frozenset[str]] | None = None
        else:
            merged_span_attrs = dict(self.allowed_span_attributes or {})
            for key, values in (other.allowed_span_attributes or {}).items():
                merged_span_attrs[key] = (
                    merged_span_attrs.get(key, frozenset()) | values
                )

        return CorpusSpec(
            open_attributes=self.open_attributes | other.open_attributes,
            closed_attributes=merged_closed,
            strict_attributes=self.strict_attributes
            or other.strict_attributes,
            allowed_span_tags=_union_optional(
                self.allowed_span_tags, other.allowed_span_tags
            ),
            allowed_span_attributes=merged_span_attrs,
            allow_alignment=self.allow_alignment and other.allow_alignment,
            allowed_alignment_fields=_union_optional(
                self.allowed_alignment_fields, other.allowed_alignment_fields
            ),
            allow_relations=self.allow_relations and other.allow_relations,
            allowed_relations=_union_optional(
                self.allowed_relations, other.allowed_relations
            ),
        )

    def has_annotation(self, name: str) -> bool:
        """Return whether *name* is a known annotation on this spec.

        An annotation is considered known when it is listed in either
        :attr:`open_attributes` or :attr:`closed_attributes`. This method is
        independent of :attr:`strict_attributes`: it only reports membership,
        not whether an unknown annotation would raise during validation.

        Args:
            name: The annotation name to check.

        Returns:
            ``True`` if *name* is either an open or closed attribute on this
            spec, ``False`` otherwise.

        Example::

            >>> spec = CorpusSpec(
            ...     open_attributes={"word"},
            ...     closed_attributes={"pos": {"NOUN", "VERB"}},
            ... )
            >>> spec.has_annotation("word")
            True
            >>> spec.has_annotation("pos")
            True
            >>> spec.has_annotation("lemma")
            False
        """
        return name in self.open_attributes or name in self.closed_attributes

    @property
    def description(self) -> str:
        """A human-readable description of this spec. Can be overridden in subclasses.
        Potentially useful for error messages, debugging, or as information to LLM agents.
        """
        parts = [f"# Corpus Specification for {self.__class__.__name__}"]

        def format_value(val, level: int = 0) -> str:
            spaces = "  " * level
            if val is None:
                return "None"
            if isinstance(val, frozenset):
                if not val:
                    return "(empty)"
                return f"{spaces}- " + f"\n{spaces}- ".join(sorted(val))
            if isinstance(val, dict):
                if not val:
                    return "(empty)"
                lines = []
                for k, v in sorted(val.items()):
                    v_str = format_value(v, level + 1)
                    nl = "\n" if v_str.strip().startswith("-") else " "
                    lines.append(f"{spaces}- {k}:{nl}{v_str}")
                return "\n".join(lines)
            if isinstance(val, bool):
                return str(val)
            return str(val)

        for field_name, field in self.model_fields.items():
            value = getattr(self, field_name)
            formatted = format_value(value)
            parts.append(f"\n## {field.description}\n{formatted}")
        return "\n".join(parts)
