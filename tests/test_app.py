"""Tests for the Gradio demo under :mod:`app.app`.

These tests skip cleanly when gradio is not installed (the ``app`` dependency
group is optional). They cover three concerns:

- Pure-Python helpers (``_parse_csv``, ``_parse_closed_attributes``,
  ``_build_custom_spec``, ``render_spec_description``).
- ``validate_query`` for valid queries, syntax errors, validation errors
  (with and without a corpus spec), and custom-spec form parsing.
- The structural shape of ``build_demo`` (presence and children of every
  Tab), which serves as a tab-navigation smoke test in lieu of a browser.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import pytest


pytest.importorskip("gradio")

# Make the repo-root ``app/`` importable without installing it as a package.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.app import (  # noqa: E402
    EMPTY_AST,
    EXAMPLES,
    PRESETS,
    TAB_LABELS,
    _build_custom_spec,
    _parse_closed_attributes,
    _parse_csv,
    build_demo,
    render_spec_description,
    validate_query,
)


DEFAULT_CUSTOM = {
    "custom_open": "",
    "custom_closed": "",
    "custom_strict": False,
    "custom_allow_alignment": True,
    "custom_allow_relations": True,
    "custom_span_tags": "",
    "custom_relations": "",
}


def _call(
    query: str,
    preset: str = "None (permissive)",
    *,
    use_custom: bool = False,
    fail_fast: bool = False,
    **overrides: object,
) -> tuple[str, str, dict, str]:
    """Tiny convenience wrapper around ``validate_query`` keyword passing."""
    fields: dict[str, object] = {**DEFAULT_CUSTOM, **overrides}
    return validate_query(
        query,
        preset,
        use_custom,
        cast(str, fields["custom_open"]),
        cast(str, fields["custom_closed"]),
        cast(bool, fields["custom_strict"]),
        cast(bool, fields["custom_allow_alignment"]),
        cast(bool, fields["custom_allow_relations"]),
        cast(str, fields["custom_span_tags"]),
        cast(str, fields["custom_relations"]),
        fail_fast,
    )


def test_parse_csv_strips_and_filters() -> None:
    assert _parse_csv("") == []
    assert _parse_csv("a, b ,  ,c") == ["a", "b", "c"]
    assert _parse_csv("a\nb\n,c") == ["a", "b", "c"]


def test_parse_closed_attributes_basic() -> None:
    text = "pos: NOUN, VERB\n# comment\n\nNumber: Sing, Plur"
    parsed = _parse_closed_attributes(text)
    assert parsed == {"pos": ["NOUN", "VERB"], "Number": ["Sing", "Plur"]}


def test_parse_closed_attributes_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        _parse_closed_attributes("not a key value line")
    with pytest.raises(ValueError):
        _parse_closed_attributes(": no key here")


def test_build_custom_spec_round_trip() -> None:
    spec = _build_custom_spec(
        open_attrs="word, lemma",
        closed_attrs="pos: NOUN, VERB",
        strict=True,
        allow_alignment=False,
        allow_relations=True,
        span_tags="s, p",
        relations="nsubj, obj",
    )
    assert spec.open_attributes == frozenset({"word", "lemma"})
    assert spec.closed_attributes == {"pos": frozenset({"NOUN", "VERB"})}
    assert spec.strict_attributes is True
    assert spec.allow_alignment is False
    assert spec.allowed_span_tags == frozenset({"s", "p"})
    assert spec.allowed_relations == frozenset({"nsubj", "obj"})


def test_validate_query_empty_input() -> None:
    status, err, ast, canonical = _call("")
    assert "Enter a BCQL query" in status
    assert err == ""
    assert ast == EMPTY_AST
    assert canonical == ""


def test_validate_query_valid_no_spec() -> None:
    status, err, ast, canonical = _call('"man"')
    assert "bcql-status-ok" in status
    assert "syntactically valid" in status
    assert err == ""
    assert ast.get("node_type")
    assert canonical.strip() == '"man"'


def test_validate_query_valid_with_ud_preset() -> None:
    status, err, ast, canonical = _call(
        '[lemma="search" & pos="NOUN"]',
        preset="Universal Dependencies (UD)",
    )
    assert "bcql-status-ok" in status
    assert "(Universal Dependencies (UD))" in status
    assert err == ""
    assert ast.get("node_type")
    assert canonical


def test_validate_query_syntax_error_has_caret_pointer() -> None:
    status, err, ast, canonical = _call('[pos="NOUN" &]')
    assert "bcql-status-err" in status
    assert "Query failed to parse" in status
    assert err.startswith("**Syntax error**")
    # The caret pointer is rendered inside a fenced code block:
    assert "```text" in err
    assert "^" in err
    assert ast == EMPTY_AST
    assert canonical == ""


def test_validate_query_validation_error_keeps_ast() -> None:
    status, err, ast, canonical = _call(
        '[pos="BANANA"]', preset="Universal Dependencies (UD)"
    )
    assert "bcql-status-err" in status
    assert "does not match the corpus spec" in status
    assert "**Validation error**" in err or "validation issue(s)" in err
    assert "invalid_annotation_value" in err
    # Even when the spec rejects it, we still parse the AST so the JSON tab
    # shows something useful:
    assert ast.get("node_type")
    assert canonical


def test_validate_query_strict_custom_rejects_unknown_attribute() -> None:
    status, err, _, _ = _call(
        '[unknownattr="x"]',
        use_custom=True,
        custom_open="word, lemma",
        custom_strict=True,
    )
    assert "bcql-status-err" in status
    assert "unknown_annotation" in err


def test_validate_query_custom_spec_form_error() -> None:
    status, err, ast, canonical = _call(
        '"x"',
        use_custom=True,
        custom_closed="malformed line without colon",
    )
    assert "bcql-status-err" in status
    assert "Custom spec error" in err
    assert ast == EMPTY_AST
    assert canonical == ""


def test_render_spec_description_for_each_preset() -> None:
    none_desc = render_spec_description("None (permissive)")
    assert "No corpus spec selected" in none_desc

    for name in PRESETS:
        if name == "None (permissive)":
            continue
        text = render_spec_description(name)
        assert "Corpus Specification" in text
        # Should contain at least one populated section:
        assert "open_attributes" in text or "Annotation" in text


def test_examples_all_run_without_crashing() -> None:
    """Every shipped example must produce a stable validate_query result.

    The example list mixes positive and intentionally broken queries, so we
    don't assert success vs failure; we only assert that each call returns
    the expected 4-tuple shape and that the status is one of the known
    HTML banners.
    """
    for query, preset in EXAMPLES:
        status, err, ast, canonical = _call(query, preset)
        assert isinstance(status, str)
        assert isinstance(err, str)
        assert isinstance(ast, dict)
        assert isinstance(canonical, str)
        assert (
            "bcql-status-ok" in status
            or "bcql-status-err" in status
            or "Enter a BCQL query" in status
        )


def _walk(node):
    """Yield every Block in the demo tree (depth-first, including ``node``)."""
    yield node
    for child in getattr(node, "children", []) or []:
        yield from _walk(child)


def test_demo_structure_has_expected_tabs() -> None:
    """The Tabs block exposes exactly the four labels we ship.

    This is the structural counterpart of "tab navigation": for each tab in
    the rendered Blocks tree we assert that the user-visible label matches
    ``TAB_LABELS`` and that the tab body contains a renderable component
    (so clicking the tab in the browser cannot land on an empty pane).
    """
    demo = build_demo()

    tab_blocks = [
        b for b in _walk(demo) if type(b).__name__ in {"Tab", "TabItem"}
    ]
    assert [getattr(t, "label", None) for t in tab_blocks] == list(TAB_LABELS)

    expected_descendant_type = {
        "AST (JSON)": "JSON",
        "Canonical BCQL": "Textbox",
        "Active spec": "Markdown",
        "About": "Markdown",
    }
    for tab in tab_blocks:
        descendant_types = {type(b).__name__ for b in _walk(tab)}
        assert len(descendant_types) > 1, (
            f"Tab {tab.label!r} has no descendant components"
        )
        expected = expected_descendant_type[tab.label]
        assert expected in descendant_types, (
            f"Tab {tab.label!r} missing {expected}; got {descendant_types}"
        )


def test_demo_structure_top_level_components() -> None:
    """Sanity-check the rest of the layout (input + button + examples).

    Ensures the page is renderable end-to-end: a query input, the Validate
    button, the status banner, and the error markdown are all present.
    """
    demo = build_demo()
    block_names = [type(b).__name__ for b in _walk(demo)]
    assert "Textbox" in block_names
    assert "Button" in block_names
    assert "Dropdown" in block_names
    assert "Tabs" in block_names
    assert "Examples" in block_names or "Dataset" in block_names
