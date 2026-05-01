"""Download BlackLab's ``Bcql.g4`` grammar file into this repository."""

# Download the latest parser definition from Github https://github.com/instituutnederlandsetaal/BlackLab
# BlackLab/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4
# Allow for specifying a branch and optionally tag (otherwise latest commit)

_DEFINITION_PATH = (
    "query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4"
)
from pathlib import Path


_CURRENT_DIR = Path(__file__).parent

import requests


def main(
    branch: str = "dev",
    tag: str | None = None,
):
    """Download ``Bcql.g4`` from GitHub and save it under ``parser/``.

    Args:
        branch: Git branch to use when ``tag`` is not provided.
        tag: Optional git tag to download from instead of ``branch``.
    """
    if tag is not None:
        url = f"https://raw.githubusercontent.com/instituutnederlandsetaal/BlackLab/{tag}/{_DEFINITION_PATH}"
    else:
        url = f"https://raw.githubusercontent.com/instituutnederlandsetaal/BlackLab/{branch}/{_DEFINITION_PATH}"
    response = requests.get(url)
    response.raise_for_status()
    pfout = _CURRENT_DIR.parent / "parser" / Path(_DEFINITION_PATH).name
    pfout.write_text(response.text, encoding="utf-8")
    print(f"Downloaded BCQL parser definition from {url} and saved to {pfout}")


def entry_point():
    """Parse CLI arguments and invoke :func:`main`."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download the latest BCQL parser definition from Github and build with ANTLR."
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="dev",
        help="The branch to download from (default: dev)",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="The tag to download (default: latest commit)",
    )
    args = parser.parse_args()

    main(branch=args.branch, tag=args.tag)


if __name__ == "__main__":
    entry_point()
