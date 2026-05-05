# Tagset / corpus validation

The parser only checks the *syntax* of a query: it has no idea which annotations your corpus
actually exposes, which POS tags are valid, or which dependency relations the corpus was
annotated with. Two queries that parse identically can have very different fates against a real
corpus: one may run, the other may silently match nothing because of a typo in a closed-class
value (``[pos="NUMBER"]`` instead of ``[pos="NUM"]``).

[`CorpusSpec`][bcql_py.CorpusSpec] closes that gap. It is a small, immutable description of a
corpus' surface vocabulary: the annotations it has, which annotations are closed-class (and the
allowed values for each), the XML span tags available, and whether dependency relations or
parallel-corpus alignment are supported. [`validate()`][bcql_py.validate] walks the parsed AST
and reports any mismatch as a [`ValidationIssue`][bcql_py.ValidationIssue].

This guide walks through:

1. What exactly a [`CorpusSpec`][bcql_py.CorpusSpec] is;
2. How to build one for your corpus;
3. How to run validation, in fail-fast and collect-all modes;
4. How to compose specs (extend / merge) and use the bundled presets.

For a runnable, copy-pasteable end-to-end example, see
[examples/validation.py](https://github.com/BramVanroy/bcql_py/blob/main/examples/validation.py).

---

## What a CorpusSpec captures

[`CorpusSpec`][bcql_py.CorpusSpec] is a frozen Pydantic model with a deliberately permissive
default: an empty ``CorpusSpec()`` accepts every valid query. You tighten it by listing only
what your corpus actually supports.

| Field | Type | What it controls |
|---|---|---|
| ``open_attributes`` | ``frozenset[str]`` | Annotations whose values are free-form (e.g. ``word``, ``lemma``). |
| ``closed_attributes`` | ``dict[str, frozenset[str]]`` | Annotations whose values must come from a fixed set (e.g. ``pos -> {"NOUN", "VERB", ...}``) |
| ``strict_attributes`` | ``bool`` | When ``True``, any annotation not listed in either of the above raises ``unknown_annotation``. Defaults to ``False`` (unknown annotations are allowed) |
| ``allowed_span_tags`` | ``frozenset[str] \| None`` | Allowed XML span tag names (e.g. ``s``, ``p``, ``ne``, ...). ``None`` = unconstrained |
| ``allowed_span_attributes`` | ``dict[str, frozenset[str]] \| None`` | Per-tag allowed XML attribute names. Tags without an entry are unconstrained |
| ``allow_alignment`` | ``bool`` | When ``False``, any use of the alignment operator ``==>`` is rejected |
| ``allowed_alignment_fields`` | ``frozenset[str] \| None`` | Allowed target field names for ``==>field`` (e.g. ``en``). ``None`` = unconstrained |
| ``allow_relations`` | ``bool`` | When ``False``, any dependency relation (``-type->`` or ``^-->``) is rejected |
| ``allowed_relations`` | ``frozenset[str] \| None`` | Allowed relation type names (usually your depedency tagset). ``None`` = unconstrained |

Every field is optional. Only the constraints you set are enforced.

!!! note "Regex values are skipped"
    The validator only checks values that are unambiguously literal (an ``l"..."`` prefix or a
    string with no regex metacharacters). A query like ``[pos="NOUN|VERB"]`` is treated as a
    regex and is *not* checked against the closed set, so you will not get false positives on
    intentional patterns. I may updated this in a future version.

---

## Building a spec for your corpus

For a small corpus you typically know exactly which annotations and tags exist. Pass them
directly to the constructor:

```python
from bcql_py import CorpusSpec

spec = CorpusSpec(
    open_attributes={"word", "lemma"},
    closed_attributes={
        "pos": {"NOUN", "VERB", "ADJ", "DET", "ADV"},
    },
    strict_attributes=True,            # reject any unknown annotation, i.e. only word, lemma, and pos allowed
    allowed_span_tags={"s", "p"},      # only sentence and paragraph spans
    allow_alignment=False,             # this corpus has no parallel data
)
```

A few notes:

- ``closed_attributes`` accepts any iterable of strings as the value; it is normalized to a
  ``frozenset`` internally.
- Setting ``strict_attributes=True`` is the difference between *"warn me when I use a tag that
  is definitely wrong"* and *"warn me whenever I touch an annotation I did not declare"*. The
  latter is recommended for production validation.
- ``allow_alignment=False`` and ``allow_relations=False`` are straightforward: they reject the
  feature entirely. Use ``allowed_alignment_fields`` / ``allowed_relations`` to allow the
  feature but constrain the values.

!!! note "CorpusSpec description for LLMs"
    You can also ask the spec for a human-readable summary, useful both for debugging and for
    including as system context in an LLM prompt:

    ```python
    print(spec.description)
    # # Corpus Specification for CorpusSpec
    #
    # ## Annotation names that can have any value
    #   - lemma
    #   - word
    # ...
    ```
---

## Validation errors

Above it is mentioned that [`ValidationIssue`][bcql_py.ValidationIssue] contains a validation error.
This is correct, however, in practice you will find that [`BCQLValidationError`][bcql_py.BCQLValidationError]
is raised instead. This is a genuine Exception that can be raised during validation, either on the first error
or after full validation. It collects the ValidationIssue's in its ``issues`` property on the exception
instance. That makes error reporting more flexible.

---

## Running validation

There are two equivalent entry points:

**1. Pass the spec to [`parse()`][bcql_py.parse].** Validation runs after a successful parse and
raises [`BCQLValidationError`][bcql_py.BCQLValidationError] on the first issue:

```python
from bcql_py import parse, BCQLValidationError

try:
    # Same spec as defined above
    parse('[pos="ADV"]', spec=spec)
except BCQLValidationError as err:
    for issue in err.issues:
        print(issue)
# [invalid_annotation_value] Value 'ADV' is not valid for closed attribute 'pos'.
# Allowed values: ADJ, DET, NOUN, VERB. (annotation='pos', value='ADV', ...)
```

**2. Validate an existing AST with [`validate()`][bcql_py.validate].** Useful when you already
have an AST (for example after programmatic manipulation) and want to validate it without
reparsing:

```python
from bcql_py import parse, validate

ast = parse('[pos="NOUN"]')
validate(ast, spec)   # same spec as defined above, validates correctly
```

### Fail-fast vs collect-all

By default validation stops at the first issue (``fail_fast=True``). Pass ``fail_fast=False``
to collect every issue in one run, which is what you want when you are surfacing errors to a
user or feeding them back to an LLM:

```python
try:
    parse('[pos="ADV" & morph="Plur"] "x" ==>nl "y"', spec=spec, fail_fast=False)
except BCQLValidationError as err:
    print(f"{len(err.issues)} issue(s):")
    for issue in err.issues:
        print(f"  - {issue}")
```

Each [`ValidationIssue`][bcql_py.ValidationIssue] carries a machine-readable ``kind`` (e.g.
``invalid_annotation_value``, ``unknown_span_tag``, ``relations_not_allowed``), a
human-readable ``message`` (with a "Did you mean ...?" suggestion when the offending value is
close to a real one), the ``node_type`` of the offending AST node, and a ``context`` dict with
the relevant identifiers.

---

## Composing specs

Real-world corpora may extend a standard tagset (Universal Dependencies, Lassy, ...) with
their own annotations and span tags. Two methods make composition cheap:

**[`extend`][bcql_py.validation.spec.CorpusSpec.extend]** adds entries on top of an existing
spec without rebuilding it from scratch:

```python
from bcql_py.validation.presets import UD

my_corpus = UD.extend(
    open_attributes={"speaker", "timestamp"},
    allowed_span_tags={"s", "p", "ne"},
    allowed_relations={"nsubj:pass", "obl:agent"},  # UD subtypes
)
```

**[`merge`][bcql_py.validation.spec.CorpusSpec.merge]** unions two whole specs. Set-valued
fields are unioned but for boolean flags, the more restrictive value wins (``False`` beats
``True``), so merging in a preset cannot silently re-enable something the caller disabled.

```python
combined = base_spec.merge(UD)
```

Both methods return a new spec; the originals are untouched.

### Bundled presets

The library ships with two ready-made specs under ``bcql_py.validation.presets``:

- ``UD`` (in [`bcql_py.validation.presets.ud`](../api/validation.md)): Universal Dependencies
  v2: universal POS tags, the core morphological feature inventory (``Number``, ``Case``,
  ``Tense``, ...), and the core dependency relation labels. Subtypes such as ``nsubj:pass``
  are intentionally excluded; add them via ``extend(allowed_relations={...})``.
- ``LASSY`` (in [`bcql_py.validation.presets.lassy`](../api/validation.md)): the Lassy /
  Alpino tagset for Dutch, with the full ``rel`` / ``cat`` / ``pt`` inventories and
  morphosyntactic features (``ntype``, ``getal``, ``graad``, ...) wired up as closed
  attributes.

Both presets are plain [`CorpusSpec`][bcql_py.CorpusSpec] instances, so they compose with
``merge`` and ``extend`` like any other spec.

---

## Writing your own preset

A preset is just a module-level [`CorpusSpec`][bcql_py.CorpusSpec] you build once and import
where needed. The pattern used by the bundled presets is:

```python
from bcql_py.validation.spec import CorpusSpec


MY_POS_TAGS: frozenset[str] = frozenset({"N", "V", "A", "P", "D"})
MY_RELATIONS: frozenset[str] = frozenset({"subj", "obj", "mod"})

MY_CORPUS = CorpusSpec(
    open_attributes={"word", "lemma"},
    closed_attributes={"pos": MY_POS_TAGS},
    allowed_relations=MY_RELATIONS,
    allowed_span_tags={"s", "p"},
)
```

If your corpus has annotations whose values you do not want to enumerate yet, list them in
``open_attributes`` instead of ``closed_attributes``. You can always tighten the spec later
without breaking existing queries.
