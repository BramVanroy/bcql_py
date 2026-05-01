"""Top-level public API for bcql_py."""

from importlib import metadata

from bcql_py.exceptions import (
    BCQLSyntaxError,
    BCQLValidationError,
    ValidationIssue,
)
from bcql_py.parser import parse, parse_from_tokens, tokenize
from bcql_py.validation import CorpusSpec, validate


try:
    __version__ = metadata.version(__name__)
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "BCQLSyntaxError",
    "BCQLValidationError",
    "ValidationIssue",
    "CorpusSpec",
    "parse",
    "parse_from_tokens",
    "tokenize",
    "validate",
]
