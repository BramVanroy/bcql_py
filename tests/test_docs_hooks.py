"""Tests for the docs post-processing hooks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


_ROOT = Path(__file__).resolve().parents[1]


def _load_hooks_module() -> ModuleType:
    """Load ``docs/hooks.py`` as a test module."""
    module_path = _ROOT / "docs" / "hooks.py"
    spec = importlib.util.spec_from_file_location(
        "bcql_py_docs_hooks", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_HOOKS = _load_hooks_module()
_REPO_URL = "https://github.com/BramVanroy/bcql_py"


class TestSourceLinkRewriting:
    """Tests for version-aware GitHub source-link rewriting."""

    def test_release_tag_links_point_to_that_tag(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Release builds should link to the tag that produced the docs."""
        monkeypatch.setenv("BCQL_PY_DOCS_SOURCE_REF", "v0.3.0")
        html = (
            '<p class="doc-source-link" markdown="span">'
            '<a data-source-link="github" '
            'href="src/bcql_py/parser/parser.py#L10-L20" '
            'target="_blank" rel="noopener">View source</a></p>'
        )

        rendered = _HOOKS.on_page_content(html, config={"repo_url": _REPO_URL})

        assert (
            'href="https://github.com/BramVanroy/bcql_py/blob/'
            'v0.3.0/src/bcql_py/parser/parser.py#L10-L20"'
        ) in rendered

    def test_links_fall_back_to_main_without_release_ref(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Local builds should keep working by defaulting source links to main."""
        monkeypatch.delenv("BCQL_PY_DOCS_SOURCE_REF", raising=False)
        html = (
            '<a data-source-link="github" '
            'href="src/bcql_py/models/base.py#L1-L2" '
            'target="_blank" rel="noopener">View source</a>'
        )

        rendered = _HOOKS.on_page_content(html, config={"repo_url": _REPO_URL})

        assert (
            'href="https://github.com/BramVanroy/bcql_py/blob/'
            'main/src/bcql_py/models/base.py#L1-L2"'
        ) in rendered


class TestDoctestRenderingHook:
    """Tests for doctest-to-highlighted-Python rendering."""

    def test_doctest_blocks_are_restyled(self) -> None:
        """Rendered doctest blocks should lose prompts and gain Python highlighting."""
        html = (
            '<div class="language-text highlight"><pre><span></span><code>'
            "&gt;&gt;&gt; print(&quot;hi&quot;)\n"
            "hi</code></pre></div>"
        )

        rendered = _HOOKS.on_page_content(html, config={"repo_url": _REPO_URL})

        assert 'class="language-python highlight"' in rendered
        assert "&gt;&gt;&gt;" not in rendered
        assert "print" in rendered
