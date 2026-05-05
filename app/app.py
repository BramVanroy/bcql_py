"""Gradio demo for ``bcql_py`` query validation.

A small, illustrative web UI that lets users paste a BlackLab Corpus Query Language
(BCQL) query, optionally pick or customize a [CorpusSpec][bcql_py.validation.CorpusSpec],
and inspect parsing / validation results in real time.

Run locally with::

    uv sync --group app
    uv run python app/app.py

The same script powers the hosted demo on Hugging Face Spaces.
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from bcql_py import (
    BCQLSyntaxError,
    BCQLValidationError,
    CorpusSpec,
    parse,
)
from bcql_py.validation.presets import LASSY, UD


PRESETS: dict[str, CorpusSpec | None] = {
    "None (permissive)": None,
    "Universal Dependencies (UD)": UD,
    "Lassy / Alpino": LASSY,
}

EXAMPLES: list[list[str]] = [
    ['"man"', "None (permissive)"],
    ['[lemma="search" & pos="NOUN"]', "Universal Dependencies (UD)"],
    ['"the" [pos="ADJ"]+ "man"', "Universal Dependencies (UD)"],
    ['<s/> containing "fluffy"', "None (permissive)"],
    ['"baker" within <ne type="PERS"/>', "None (permissive)"],
    ['[pos="VERB"] -nsubj-> [pos="NOUN"]', "Universal Dependencies (UD)"],
    ['A:[pos="ADJ"] "man"', "Universal Dependencies (UD)"],
    ['[pos="NOUN" &]', "None (permissive)"],
    ['[pos="BANANA"]', "Universal Dependencies (UD)"],
    ['[unknownattr="x"]', "Universal Dependencies (UD)"],
]

TAB_LABELS: tuple[str, ...] = (
    "AST (JSON)",
    "Active spec",
)


# Indigo (mkdocs-material primary) shades:
INDIGO = gr.themes.Color(
    name="indigo",
    c50="#e8eaf6",
    c100="#c5cae9",
    c200="#9fa8da",
    c300="#7986cb",
    c400="#5c6bc0",
    c500="#3f51b5",
    c600="#3949ab",
    c700="#303f9f",
    c800="#283593",
    c900="#1a237e",
    c950="#0d1442",
)

THEME = gr.themes.Soft(
    primary_hue=INDIGO,
    secondary_hue=INDIGO,
    neutral_hue="slate",
    font=(
        gr.themes.GoogleFont("Roboto"),
        "ui-sans-serif",
        "system-ui",
        "sans-serif",
    ),
    font_mono=(
        gr.themes.GoogleFont("Roboto Mono"),
        "ui-monospace",
        "Consolas",
        "monospace",
    ),
).set(
    body_background_fill="*neutral_50",
    body_background_fill_dark="*neutral_950",
    block_radius="*radius_lg",
    button_primary_background_fill="*primary_500",
    button_primary_background_fill_hover="*primary_600",
    button_primary_text_color="white",
)

# Theming: https://www.gradio.app/guides/theming-guide#extending-themes-via-set
CUSTOM_CSS = """
.bcql-header {
    text-align: center;
    padding: 1.25rem 0 0.5rem 0;
}
.bcql-header h1 {
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0;
}
.bcql-header p {
    color: var(--body-text-color-subdued);
    margin-top: 0.4rem;
}
.bcql-status-ok {
    background: linear-gradient(90deg, #e8f5e9 0%, #f1f8e9 100%);
    border-left: 4px solid #2e7d32;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    color: #1b5e20;
    font-weight: 600;
}
.bcql-status-err {
    background: linear-gradient(90deg, #ffebee 0%, #fff3e0 100%);
    border-left: 4px solid #c62828;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    color: #b71c1c;
    font-weight: 600;
}
.dark .bcql-status-ok {
    background: rgba(46, 125, 50, 0.15);
    color: #a5d6a7;
}
.dark .bcql-status-err {
    background: rgba(198, 40, 40, 0.18);
    color: #ef9a9a;
}
.bcql-footer {
    text-align: center;
    color: var(--body-text-color-subdued);
    padding: 1rem 0 0.5rem 0;
    font-size: 0.9rem;
}
"""

EMPTY_AST: dict[str, Any] = {}
EMPTY_STATUS: str = (
    '<div class="bcql-status-ok" style="opacity: 0.6;">'
    "Enter a BCQL query above and click <b>Validate query</b>.</div>"
)


def _parse_csv(value: str) -> list[str]:
    """Split a comma/whitespace-separated string into a clean list of names."""
    if not value:
        return []
    parts: list[str] = []
    for chunk in value.replace("\n", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def _parse_closed_attributes(text: str) -> dict[str, list[str]]:
    """Parse a textarea of ``key: val1, val2`` lines into a dict.

    Lines starting with ``#`` and blank lines are ignored. Raises ``ValueError``
    on malformed lines so the UI can show a friendly error.
    """
    result: dict[str, list[str]] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(
                f"Closed attributes line must look like 'key: val1, val2': {raw!r}"
            )
        key, _, values = line.partition(":")
        key = key.strip()
        if not key:
            raise ValueError(f"Empty annotation name in line: {raw!r}")
        result[key] = _parse_csv(values)
    return result


def _build_custom_spec(
    open_attrs: str,
    closed_attrs: str,
    strict: bool,
    allow_alignment: bool,
    allow_relations: bool,
    span_tags: str,
    relations: str,
) -> CorpusSpec:
    """Construct a [CorpusSpec][bcql_py.validation.CorpusSpec] from the custom-spec form fields."""
    closed = _parse_closed_attributes(closed_attrs)
    span_tag_list = _parse_csv(span_tags)
    relation_list = _parse_csv(relations)
    return CorpusSpec(
        open_attributes=frozenset(_parse_csv(open_attrs)),
        closed_attributes={k: frozenset(v) for k, v in closed.items()},
        strict_attributes=strict,
        allow_alignment=allow_alignment,
        allow_relations=allow_relations,
        allowed_span_tags=frozenset(span_tag_list) if span_tag_list else None,
        allowed_relations=frozenset(relation_list) if relation_list else None,
    )


def _format_syntax_error(error: BCQLSyntaxError) -> str:
    """Format a [BCQLSyntaxError][bcql_py.exceptions.BCQLSyntaxError] as a fenced markdown snippet with caret."""
    lines = ["**Syntax error**", "", f"> {error.message}"]
    if error.query and error.position is not None:
        lines.extend(
            [
                "",
                "```text",
                error.query,
                " " * error.position + "^",
                "```",
            ]
        )
    return "\n".join(lines)


def _format_validation_error(error: BCQLValidationError) -> str:
    """Format a [BCQLValidationError][bcql_py.exceptions.BCQLValidationError] as a markdown bullet list."""
    if len(error.issues) == 1:
        issue = error.issues[0]
        parts = [
            "**Validation error**",
            "",
            f"- **{issue.kind}**: {issue.message}",
        ]
        if issue.context:
            parts.append("")
            parts.append("**Context:**")
            for key, val in issue.context.items():
                parts.append(f"  - {key}: {val!r}")
        return "\n".join(parts)

    parts = [f"**Found {len(error.issues)} validation issue(s):**", ""]
    for issue in error.issues:
        parts.append(f"- **{issue.kind}**: {issue.message}")
        if issue.context:
            ctx = ", ".join(f"`{k}={v!r}`" for k, v in issue.context.items())
            parts.append(f"  - {ctx}")
    return "\n".join(parts)


def _ok_html(message: str) -> str:
    return f'<div class="bcql-status-ok">✅ {message}</div>'


def _err_html(message: str) -> str:
    return f'<div class="bcql-status-err">❌ {message}</div>'


def validate_query(
    query: str,
    preset_name: str,
    use_custom: bool,
    custom_open: str,
    custom_closed: str,
    custom_strict: bool,
    custom_allow_alignment: bool,
    custom_allow_relations: bool,
    custom_span_tags: str,
    custom_relations: str,
    fail_fast: bool,
) -> tuple[str, str, dict[str, Any]]:
    """Run the parser/validator and return UI-ready values.

    Returns:
        Tuple of ``(status_html, error_markdown, ast_dict, canonical_bcql)``.
        ``ast_dict`` is a plain dict; empty when no AST was produced.
    """
    query = (query or "").strip()
    if not query:
        return (EMPTY_STATUS, "", EMPTY_AST)

    spec: CorpusSpec | None
    if use_custom:
        try:
            spec = _build_custom_spec(
                custom_open,
                custom_closed,
                custom_strict,
                custom_allow_alignment,
                custom_allow_relations,
                custom_span_tags,
                custom_relations,
            )
        except ValueError as exc:
            return (
                _err_html("Invalid custom corpus spec."),
                f"**Custom spec error**\n\n> {exc}",
                EMPTY_AST,
            )
    else:
        spec = PRESETS.get(preset_name)

    try:
        ast = parse(query, spec=spec, fail_fast=fail_fast)
    except BCQLSyntaxError as exc:
        return (
            _err_html("Query failed to parse."),
            _format_syntax_error(exc),
            EMPTY_AST,
        )
    except BCQLValidationError as exc:
        # Try to also surface the parsed AST when validation (not parsing) fails:
        try:
            ast_only = parse(query)
            ast_dict = ast_only.model_dump(mode="json")
        except Exception:
            ast_dict = EMPTY_AST
        return (
            _err_html(
                "Query syntactically parses but does not match the corpus spec."
            ),
            _format_validation_error(exc),
            ast_dict,
        )

    label = (
        "Query is syntactically valid."
        if spec is None
        else (
            "Query is valid against the selected corpus spec "
            f"({'custom' if use_custom else preset_name})."
        )
    )
    return (_ok_html(label), "", ast.model_dump(mode="json"))


def validate_example(
    query: str, preset_name: str
) -> tuple[str, str, dict[str, Any]]:
    """Wrapper around validate_query for ``gr.Examples`` (2-arg signature)."""
    return validate_query(
        query, preset_name, False, "", "", False, True, True, "", "", False
    )


def render_spec_description(preset_name: str) -> str:
    """Markdown description of the selected preset's [CorpusSpec][bcql_py.validation.CorpusSpec]."""
    spec = PRESETS.get(preset_name)
    if spec is None:
        return (
            "_No corpus spec selected: only syntactic parsing is performed._\n\n"
            "Pick a preset or enable **Custom corpus spec** to also run "
            "semantic validation against a corpus vocabulary."
        )
    return spec.description


INTRO_HTML = """
<div class="bcql-header">
  <h1>BCQL Validator</h1>
  <p>Parse and validate <strong><a href="https://blacklab.ivdnt.org/" target="_blank">BlackLab</a></strong>
  Corpus Query Language queries with
  <strong><a href="https://bramvanroy.github.io/bcql_py/" target="_blank"><code>bcql_py</code></a></strong></p>
</div>
"""

ABOUT_MARKDOWN = """
## About

`bcql_py` is a Python parser for the BlackLab Corpus Query Language. It produces
a frozen Pydantic AST that round-trips back to BCQL or JSON, and ships an
optional semantic validation layer driven by a `CorpusSpec`.

This demo lets you:

- **Parse** any BCQL query and see the resulting AST as JSON.
- **Validate** the query against a built-in preset (`UD`, `Lassy`) or a
  custom corpus spec you define on the fly.

When parsing or validation fails, the error message points at the offending
position in the query: useful both for humans and for LLM-driven feedback
loops.

**Links:** [GitHub](https://github.com/BramVanroy/bcql_py) ·
[Documentation](https://bramvanroy.github.io/bcql_py/) ·
[BCQL cheatsheet](https://bramvanroy.github.io/bcql_py/guides/cheatsheet/)
"""

with gr.Blocks(
    title="BCQL Validator",
    analytics_enabled=False,
) as demo:
    # Heading
    gr.HTML(INTRO_HTML)

    # Sidebar with about text
    with gr.Sidebar(position="right"):
        gr.Markdown(ABOUT_MARKDOWN)

    # Main content: query input and results
    with gr.Row(equal_height=False):
        # Main column for input (query, spec, examples)
        with gr.Column(scale=5):
            query_input = gr.Textbox(
                label="BCQL query",
                value='[lemma="search" & pos="NOUN"]',
                lines=4,
                max_lines=12,
                placeholder='[pos="NOUN"]   "the" [pos="ADJ"]+ "man"   ...',
            )

            with gr.Row():
                preset_dropdown = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="None (permissive)",
                    label="Corpus preset",
                    scale=3,
                )
                fail_fast = gr.Checkbox(
                    value=False,
                    label="Fail fast",
                    info="Stop at the first issue instead of collecting all.",
                    scale=2,
                )

            with gr.Accordion("Custom corpus spec (advanced)", open=False):
                use_custom = gr.Checkbox(
                    value=False,
                    label="Use custom spec instead of preset",
                )
                custom_open = gr.Textbox(
                    label="Open attributes",
                    placeholder="word, lemma, xpos",
                    info="Comma-separated annotation names with unconstrained values.",
                )
                custom_closed = gr.Textbox(
                    label="Closed attributes",
                    placeholder="pos: NOUN, VERB, ADJ\nNumber: Sing, Plur",
                    info="One per line: 'name: value1, value2, ...'.",
                    lines=4,
                )
                with gr.Row():
                    custom_strict = gr.Checkbox(
                        value=False,
                        label="Strict attributes",
                        info="Reject any annotation not listed above.",
                    )
                    custom_allow_alignment = gr.Checkbox(
                        value=True, label="Allow alignment (==>)"
                    )
                    custom_allow_relations = gr.Checkbox(
                        value=True, label="Allow relations (-->)"
                    )
                custom_span_tags = gr.Textbox(
                    label="Allowed span tags",
                    placeholder="s, p, ne",
                    info="Leave empty to allow any tag.",
                )
                custom_relations = gr.Textbox(
                    label="Allowed relation labels",
                    placeholder="nsubj, obj, amod",
                    info="Leave empty to allow any relation label.",
                )

            validate_btn = gr.Button(
                "Validate query", variant="primary", size="lg"
            )

        # Column for outputs (status, error, AST, canonical BCQL)
        with gr.Column(scale=4):
            status_box = gr.HTML(value=EMPTY_STATUS, label="Status")
            error_md = gr.Markdown(
                value="",
                label="Error details",
                latex_delimiters=None,
            )

            with gr.Tabs():
                with gr.Tab(TAB_LABELS[0], render_children=True):
                    ast_output = gr.JSON(value=EMPTY_AST, label="")
                with gr.Tab(TAB_LABELS[1], render_children=True):
                    spec_md = gr.Markdown(
                        value=render_spec_description("None (permissive)"),
                    )
    inputs = [
        query_input,
        preset_dropdown,
        use_custom,
        custom_open,
        custom_closed,
        custom_strict,
        custom_allow_alignment,
        custom_allow_relations,
        custom_span_tags,
        custom_relations,
        fail_fast,
    ]
    outputs = [status_box, error_md, ast_output]

    with gr.Row():
        gr.Examples(
            examples=EXAMPLES,
            inputs=inputs[:2],
            outputs=outputs,
            label="Examples",
            examples_per_page=10,
            cache_examples=True,
            fn=validate_example,
            preload=5,
        )

    gr.HTML(
        '<div class="bcql-footer">Built with '
        '<a href="https://bramvanroy.github.io/bcql_py/">bcql_py</a> · '
        '<a href="https://gradio.app/">Gradio</a></div>'
    )

    validate_btn.click(validate_query, inputs=inputs, outputs=outputs)
    # On preset change, refresh the Active spec tab and re-validate.
    preset_dropdown.change(
        render_spec_description,
        inputs=preset_dropdown,
        outputs=spec_md,
    )
    preset_dropdown.change(validate_query, inputs=inputs, outputs=outputs)
    use_custom.change(validate_query, inputs=inputs, outputs=outputs)

demo.launch(theme=THEME, css=CUSTOM_CSS)
