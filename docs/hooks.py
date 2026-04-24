"""MkDocs hook: render doctest Examples sections as clean, syntax-highlighted Python.

Docstrings use ``>>>`` prompts so that ``pytest --doctest-modules`` can run them.
This hook post-processes the rendered HTML: it finds the plain-text blocks that
mkdocstrings generates for ``Examples::`` sections, strips the ``>>>`` / ``...``
prompts, then re-highlights the resulting code with Pygments as Python: giving
readers a clean, copyable, syntax-coloured block.

Doctests in source files are NOT modified: only the rendered HTML differs.
"""

from __future__ import annotations

import html as html_lib
import re

from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

_lexer = PythonLexer()
_formatter = HtmlFormatter(nowrap=True)


def _strip_doctest_prompts(code: str) -> str:
    """
    - Strip ``>>> `` and ``... `` prompts portions of examples in docstrings;
    - convert output lines to ``# comments``.

    Does smart handling of output in the examples so that it gets written to a comment in the documentation.
    """
    lines = code.split("\n")
    result: list[str] = []
    expect_output = False

    for line in lines:
        if line.startswith(">>> "):
            result.append(line[4:])
            expect_output = True
        elif line == ">>>":
            result.append("")
            expect_output = False
        elif line.startswith("... "):
            result.append(line[4:])
        elif line == "...":
            result.append("")
        elif expect_output and line != "":
            result.append("# " + line)
            expect_output = False
        else:
            result.append(line)
            if line.strip():
                expect_output = False

    return "\n".join(result).strip()


def on_page_content(html: str, **kwargs) -> str:
    """Post-process rendered page HTML to fix doctest blocks."""

    def transform_block(m: re.Match) -> str:
        raw_code = m.group(1)
        if "&gt;&gt;&gt;" not in raw_code:
            return m.group(0)
        clean = _strip_doctest_prompts(html_lib.unescape(raw_code))
        inner = pyg_highlight(clean, _lexer, _formatter)
        return (
            '<div class="language-python highlight">'
            "<pre><span></span><code>"
            + inner
            + "</code></pre></div>"
        )

    return re.sub(
        r'<div class="language-text highlight"><pre[^>]*><span></span><code>(.*?)</code></pre></div>',
        transform_block,
        html,
        flags=re.DOTALL,
    )
