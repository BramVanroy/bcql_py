from importlib import metadata

from bcql_py.exceptions import BCQLSyntaxError
from bcql_py.parser import parse, parse_from_tokens, tokenize


try:
    __version__ = metadata.version(__name__)
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "BCQLSyntaxError",
    "parse",
    "parse_from_tokens",
    "tokenize",
]
