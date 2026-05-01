"""Download BlackLab's ``Bcql.g4`` grammar file into this repository."""

from pathlib import Path


_CURRENT_DIR = Path(__file__).parent

from bcql_py.utils import get_blacklab_g4_grammar


def main(
    branch: str = "dev",
    tag: str | None = None,
):
    """Download ``Bcql.g4`` from GitHub and save it under ``parser/``.

    Args:
        branch: Git branch to use when ``tag`` is not provided.
        tag: Optional git tag to download from instead of ``branch``.
    """
    pfout = _CURRENT_DIR.parent / "parser" / "Bcql.g4"
    get_blacklab_g4_grammar(output_path=pfout, branch=branch, tag=tag)


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
