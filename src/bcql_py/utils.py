"""Utility functions for BCQL parser generation and testing."""

from pathlib import Path

import requests


def get_blacklab_g4_grammar(
    output_path: Path | str | None = None,
    *,
    branch: str = "dev",
    tag: str | None = None,
) -> str:
    """Download ``Bcql.g4`` from GitHub, return it and optionally save it to a file.

    Args:
        output_path: Optional path to write the downloaded grammar to.
        branch: Git branch to use when ``tag`` is not provided.
        tag: Optional git tag to download from instead of ``branch``.
    """
    if tag is not None:
        url = f"https://raw.githubusercontent.com/instituutnederlandsetaal/BlackLab/{tag}/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4"
    else:
        url = f"https://raw.githubusercontent.com/instituutnederlandsetaal/BlackLab/{branch}/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4"

    response = requests.get(url)
    response.raise_for_status()
    content = response.text

    if output_path is not None:
        pfout = Path(output_path)
        pfout.write_text(content, encoding="utf-8")

    return content
