"""Semantic validation for BCQL queries.

The parser produces a purely syntactic AST but real corpora impose extra rules: which
annotations exist, which values a closed-class attribute may take, which XML spans
are available, and whether alignment / relation queries are meaningful. The
:class:`CorpusSpec` describes those rules, and :func:`validate` walks a parsed
:class:`~bcql_py.models.base.BCQLNode` tree to verify them.

Typical usage::

    from bcql_py import parse
    from bcql_py.validation import CorpusSpec
    from bcql_py.validation.presets import UD_POS, UD_RELATIONS

    spec = CorpusSpec(open_attributes={"word", "lemma"}).merge(UD_POS).merge(UD_RELATIONS)
    ast = parse('[pos="NOUN"]', spec=spec)
"""

from bcql_py.exceptions import BCQLValidationError, ValidationIssue
from bcql_py.validation.spec import CorpusSpec
from bcql_py.validation.validator import validate


__all__ = [
    "CorpusSpec",
    "ValidationIssue",
    "BCQLValidationError",
    "validate",
]
