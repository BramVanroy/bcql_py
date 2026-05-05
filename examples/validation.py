"""BCQL validation: syntactic, structural, and semantic.

The library validates a query at three different layers:

1. **Lexical / syntactic** -- [parse()][bcql_py.parser.parse] rejects malformed input with a
   [BCQLSyntaxError][bcql_py.exceptions.BCQLSyntaxError] that points at the offending character.
2. **Structural** -- the immutable Pydantic AST nodes themselves enforce
   invariants (sequences need at least two children, repetition counts cannot be
   negative, and so on). Constructing a bad node raises ``pydantic.ValidationError``.
3. **Semantic** -- a [CorpusSpec][bcql_py.validation.CorpusSpec] describes which annotations, span tags,
   alignment fields, and dependency relations a particular corpus actually
   supports. ``parse(query, spec=spec)`` runs the spec checks after a successful
   parse, collecting [ValidationIssue][bcql_py.exceptions.ValidationIssue] objects via
   [BCQLValidationError][bcql_py.exceptions.BCQLValidationError].

Each section below prints intermediary output so it is easy to see what each
layer rejects and what the resulting error messages look like.
"""

from __future__ import annotations

from pydantic import ValidationError

from bcql_py import (
    BCQLSyntaxError,
    BCQLValidationError,
    CorpusSpec,
    parse,
    validate,
)
from bcql_py.models import (
    RepetitionNode,
    SequenceNode,
    StringValue,
    TokenQuery,
)
from bcql_py.validation.presets import UD


SECTION_SEPARATOR = "=" * 70


def print_section(title: str) -> None:
    """Print a clearly delimited section header.

    Args:
        title: The title to display.
    """
    print(f"\n{SECTION_SEPARATOR}\n{title}\n{SECTION_SEPARATOR}")


def try_parse(
    query: str, *, spec: CorpusSpec | None = None, fail_fast: bool = True
) -> None:
    """Parse ``query`` and print the outcome (success, syntax error, or validation error).

    Args:
        query: The BCQL query to parse.
        spec: Optional corpus spec for semantic validation.
        fail_fast: Forwarded to [parse()][bcql_py.parser.parse].
    """
    print(f"\nQuery: {query!r}")
    try:
        ast = parse(query, spec=spec, fail_fast=fail_fast)
    except BCQLSyntaxError as err:
        print("  -> BCQLSyntaxError:")
        for line in str(err).splitlines():
            print(f"     {line}")
    except BCQLValidationError as err:
        print(f"  -> BCQLValidationError ({len(err.issues)} issue(s)):")
        for issue in err.issues:
            print(f"     {issue}")
    else:
        print(f"  -> OK: {ast.to_bcql()}")


print_section("1. Syntactic validation: the parser rejects malformed queries")

# Each of these is rejected at parse time with a BCQLSyntaxError. The error
# message embeds the original query plus a caret (^) pointing at the position
# the parser stumbled on, which makes it easy to feed back to a user or LLM.
syntax_examples = [
    '[word="baker"',  # unclosed bracket
    '[word="baker"))',  # stray paren
    '"the" [pos=]',  # missing value
    '[pos="NOUN" &]',  # dangling boolean operator
    '"hello" "',  # unterminated string
]
for query in syntax_examples:
    try_parse(query)


print_section(
    "2. Structural validation: AST nodes enforce their own invariants"
)

# The AST models are frozen Pydantic v2 models with field constraints. They
# refuse to be built with values that would produce a structurally meaningless
# tree, even if you bypass the parser and construct them by hand.

# A SequenceNode requires at least two children (use a single child directly
# instead of wrapping it in a sequence).
print("\nBuilding SequenceNode with only one child:")
try:
    SequenceNode(children=[TokenQuery(shorthand=StringValue(value="the"))])
except ValidationError as err:
    print(f"  -> pydantic.ValidationError:\n     {err}")

# RepetitionNode's min_count must be >= 0; max_count must be >= min_count
# when set (covered by Pydantic's ``ge`` and the model's own checks).
print("\nBuilding RepetitionNode with min_count=-1:")
try:
    RepetitionNode(
        child=TokenQuery(shorthand=StringValue(value="x")),
        min_count=-1,
    )
except ValidationError as err:
    print(f"  -> pydantic.ValidationError:\n     {err}")

# Pydantic also rejects unknown fields and bad enum values via the
# discriminated union: a ``node_type`` that does not exist cannot be
# materialized from JSON.
print("\nDeserializing JSON with unknown node_type:")
bad_json = '{"node_type": "not_a_real_node", "value": "x"}'
try:
    StringValue.model_validate_json(bad_json)
except ValidationError as err:
    print(f"  -> pydantic.ValidationError:\n     {err}")


print_section("3. Semantic validation with a custom CorpusSpec")

# A CorpusSpec describes the surface vocabulary your corpus actually supports:
# which annotations exist, which are closed-class (pos, deprel, ...), which XML
# spans are available, and whether alignment / relations queries are allowed.
#
# Defaults are maximally permissive ("anything goes"). Tighten the spec only
# for the fields you actually want to enforce.
my_spec = CorpusSpec(
    open_attributes={"word", "lemma"},
    closed_attributes={"pos": {"NOUN", "VERB", "ADJ", "DET"}},
    strict_attributes=True,  # reject any unknown annotation
    allowed_span_tags={"s", "p"},  # only sentence and paragraph spans
    allow_alignment=False,  # this corpus has no parallel data
)

# Print the spec's human-readable description, useful for error messages and
# for handing context to LLMs.
print(my_spec.description)

# A query that fits the spec is accepted.
try_parse('[pos="NOUN"]', spec=my_spec)

# A closed-class value outside the allowed set is reported with a hint.
try_parse('[pos="ADV"]', spec=my_spec)

# An unknown annotation under ``strict_attributes=True`` is also rejected.
try_parse('[lemma="run" & morph="Plur"]', spec=my_spec)

# Disallowed span tags are reported.
try_parse("<ne/>", spec=my_spec)

# Alignment queries are blocked entirely.
try_parse('"book" ==>nl "boek"', spec=my_spec)


print_section("4. Collecting every issue at once with fail_fast=False")

# By default ``parse`` (and ``validate``) stop at the first issue. Pass
# ``fail_fast=False`` to collect every problem so the user / LLM can see them
# all in one shot.
multi_issue_query = '[pos="ADV" & lemma="run" & morph="Plur"] "x" ==>nl "y"'
try_parse(multi_issue_query, spec=my_spec, fail_fast=False)


print_section("5. Using the bundled UD preset")

# The library ships with a Universal Dependencies preset (``UD``) that wires up
# the universal POS tags, common feature attributes, and dependency relation
# labels. It is a CorpusSpec and so composes via ``.merge`` and ``.extend``.

print(f"UD has {len(UD.open_attributes)} open attributes")
print(
    f"UD has {len(UD.closed_attributes)} closed attributes (pos, deprel, feats...)"
)
print(f"UD allows {len(UD.allowed_relations or [])} relation labels")

# A query against the UD vocabulary passes:
try_parse('[pos="NOUN" & Number="Sing"]', spec=UD)

# An invalid POS tag is reported with a "did you mean ..." hint:
try_parse('[pos="NUMBER"]', spec=UD)

# An invalid relation label is also rejected:
try_parse('_ -nsbj-> [pos="NOUN"]', spec=UD)


print_section("6. Extending a preset for a specific corpus")

# Real-world corpora extend a preset with their own annotations, span tags,
# and relation subtypes. ``extend`` returns a new (immutable) spec.
my_corpus = UD.extend(
    open_attributes={"speaker", "timestamp"},
    allowed_span_tags={"s", "p", "ne"},
    allowed_relations={"nsubj:pass", "obl:agent"},
)

# UD-only relation: still valid because it is in the base preset.
try_parse('_ -nsubj-> [pos="VERB"]', spec=my_corpus)

# Subtype added on top of UD: now valid.
try_parse('_ -nsubj:pass-> [pos="VERB"]', spec=my_corpus)

# Custom open attribute also valid.
try_parse('[speaker="Alice"]', spec=my_corpus)


print_section("7. Validating an already-parsed AST")

# If you already have an AST (for instance after manipulating it programmatically)
# you can run validation directly without re-parsing.
ast = parse('[pos="NOUN"] [pos="DET"]')
try:
    validate(ast, my_spec)
    print("AST validates against my_spec")
except BCQLValidationError as err:
    print(f"AST does not validate: {err}")
