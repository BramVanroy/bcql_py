"""Full Universal Dependencies (UD v2) preset.

- Universal POS tags (``UD_POS_TAGS``, wired as closed values for the
  ``upos`` annotations).
- Universal morphological features (``UD_FEATURE_VALUES``), each one a
  closed attribute (``Number``, ``Case``, ``PronType``, ...).
- Core universal dependency relation labels (``UD_RELATION_LABELS``, wired
  as allowed relation values; the relation label is also exposed
  as the closed ``deprel`` annotation for corpora that store it on the token.
- Common CoNLL-U-style open annotations (``UD_OPEN_ATTRIBUTES``):
  ``word``, ``lemma``, ``xpos``, ``feats``, ``misc``, plus ``id``, ``head``.

References:
    - POS: https://universaldependencies.org/u/pos/all.html
    - Features: https://universaldependencies.org/u/feat/all.html
    - Relations: https://universaldependencies.org/u/dep/all.html

Language-specific POS sub-types and relation subtypes (e.g. ``nsubj:pass``)
are intentionally not included. Extend the preset to add them::

    spec = UD.extend(allowed_relations={"nsubj:pass", "acl:relcl", "obl:agent"})
"""

from __future__ import annotations

from bcql_py.validation.spec import CorpusSpec


UD_POS_TAGS: frozenset[str] = frozenset(
    {
        "ADJ",
        "ADP",
        "ADV",
        "AUX",
        "CCONJ",
        "DET",
        "INTJ",
        "NOUN",
        "NUM",
        "PART",
        "PRON",
        "PROPN",
        "PUNCT",
        "SCONJ",
        "SYM",
        "VERB",
        "X",
    }
)
"""Universal Dependencies v2 universal POS tags.

Wired as closed attribute values for the ``upos`` annotation in the UD preset.
See https://universaldependencies.org/u/pos/all.html for details.
"""

# NOTE: that we do not include subtypes such as ``advcl:relcl`` or ``nsubj:pass``
# NOTE: "root" tag is not included since that should only be assigned to a sentinel node,
# not to any token in the corpus
UD_RELATION_LABELS: frozenset[str] = frozenset(
    {
        "acl",
        "advcl",
        "advmod",
        "amod",
        "appos",
        "aux",
        "case",
        "cc",
        "ccomp",
        "clf",
        "compound",
        "conj",
        "cop",
        "csubj",
        "dep",
        "det",
        "discourse",
        "dislocated",
        "expl",
        "fixed",
        "flat",
        "goeswith",
        "iobj",
        "list",
        "mark",
        "nmod",
        "nsubj",
        "nummod",
        "obj",
        "obl",
        "orphan",
        "parataxis",
        "punct",
        "reparandum",
        "vocative",
        "xcomp",
    }
)
"""Core Universal Dependencies v2 dependency relation labels.

Wired as allowed relation values in the UD preset.
Language-specific subtypes (e.g., ``nsubj:pass``, ``acl:relcl``) are not included; extend the preset to add them.
See https://universaldependencies.org/u/dep/all.html for full documentation.
"""

UD_FEATURE_VALUES: dict[str, frozenset[str]] = {
    # Lexical
    "PronType": frozenset(
        {
            "Art",
            "Dem",
            "Emp",
            "Exc",
            "Ind",
            "Int",
            "Neg",
            "Prs",
            "Rcp",
            "Rel",
            "Tot",
        }
    ),
    "NumType": frozenset(
        {"Card", "Dist", "Frac", "Mult", "Ord", "Range", "Sets"}
    ),
    "Poss": frozenset({"Yes"}),
    "Reflex": frozenset({"Yes"}),
    # Other
    "Foreign": frozenset({"Yes"}),
    "Abbr": frozenset({"Yes"}),
    "Typo": frozenset({"Yes"}),
    "ExtPos": frozenset(
        {
            "ADJ",
            "ADP",
            "ADV",
            "AUX",
            "CCONJ",
            "DET",
            "INTJ",
            "PRON",
            "PROPN",
            "SCONJ",
        }
    ),
    # Inflection
    "Gender": frozenset({"Com", "Fem", "Masc", "Neut"}),
    "Animacy": frozenset({"Anim", "Hum", "Inan", "Nhum"}),
    "NounClass": frozenset(
        {
            "Bantu1",
            "Bantu2",
            "Bantu3",
            "Bantu4",
            "Bantu5",
            "Bantu6",
            "Bantu7",
            "Bantu8",
            "Bantu9",
            "Bantu10",
            "Bantu11",
            "Bantu12",
            "Bantu13",
            "Bantu14",
            "Bantu15",
            "Bantu16",
            "Bantu17",
            "Bantu18",
            "Bantu19",
            "Bantu20",
            "Bantu21",
            "Bantu22",
            "Bantu23",
            "Wol1",
            "Wol2",
            "Wol3",
            "Wol4",
            "Wol5",
            "Wol6",
            "Wol7",
            "Wol8",
            "Wol9",
            "Wol10",
            "Wol11",
            "Wol12",
        }
    ),
    "Number": frozenset(
        {
            "Coll",
            "Count",
            "Dual",
            "Grpa",
            "Grpl",
            "Inv",
            "Pauc",
            "Plur",
            "Ptan",
            "Sing",
            "Tri",
        }
    ),
    # Only the "core" values are included here, see: https://universaldependencies.org/u/feat/all.html#case-case
    "Case": frozenset({"Abs", "Acc", "Erg", "Nom"}),
    "Definite": frozenset({"Com", "Cons", "Def", "Ind", "Spec"}),
    # Abv	Bel	Even	Med	Nvis	Prox	Remt
    "Deixis": frozenset({"Abv", "Bel", "Even", "Med", "Nvis", "Prx", "Remt"}),
    "DeixisRef": frozenset({"1", "2"}),
    "Degree": frozenset({"Abs", "Aug", "Cmp", "Dim", "Equ", "Pos", "Sup"}),
    "VerbForm": frozenset(
        {"Conv", "Fin", "Gdv", "Ger", "Inf", "Part", "Sup", "Vnoun"}
    ),
    "Mood": frozenset(
        {
            "Adm",
            "Cnd",
            "Des",
            "Imp",
            "Ind",
            "Int",
            "Irr",
            "Jus",
            "Nec",
            "Opt",
            "Pot",
            "Prp",
            "Qot",
            "Sub",
        }
    ),
    "Tense": frozenset({"Fut", "Imp", "Past", "Pqp", "Pres"}),
    "Aspect": frozenset({"Hab", "Imp", "Iter", "Perf", "Prog", "Prosp"}),
    "Voice": frozenset(
        {
            "Act",
            "Antip",
            "Bfoc",
            "Cau",
            "Dir",
            "Inv",
            "Lfoc",
            "Mid",
            "Pass",
            "Rcp",
        }
    ),
    "Evident": frozenset({"Fh", "Nfh"}),
    "Polarity": frozenset({"Neg", "Pos"}),
    "Person": frozenset({"0", "1", "2", "3", "4"}),
    "Polite": frozenset({"Elev", "Form", "Humb", "Infm"}),
    "Clusivity": frozenset({"Ex", "In"}),
}
"""Universal morphological features and their allowed values.

Wired as closed attributes in the UD preset (e.g., ``Number``, ``Case``, ``Tense``, etc.).
See https://universaldependencies.org/u/feat/all.html for complete documentation.
"""

UD_OPEN_ATTRIBUTES: frozenset[str] = frozenset(
    {"word", "lemma", "xpos", "feats", "misc", "id", "head"}
)
"""Common CoNLL-U open annotations in Universal Dependencies.

Open attributes are those whose values are not restricted to a fixed set.
Includes token form, lemma, extended POS tag, features, metadata, ID, and head index.
"""

_UD_CLOSED_ATTRIBUTES: dict[str, frozenset[str]] = {
    "upos": UD_POS_TAGS,
    "pos": UD_POS_TAGS,
    "deprel": UD_RELATION_LABELS,
    **UD_FEATURE_VALUES,
}

UD = CorpusSpec(
    open_attributes=UD_OPEN_ATTRIBUTES,
    closed_attributes=_UD_CLOSED_ATTRIBUTES,
    allowed_relations=UD_RELATION_LABELS,
)
"""Universal Dependencies v2 corpus specification.

A ready-made [CorpusSpec][bcql_py.validation.spec.CorpusSpec] for validating BCQL queries against
Universal Dependencies v2 corpora. Includes universal POS tags, morphological features, core dependency
relations, and standard CoNLL-U annotations.

Language-specific subtypes and variations can be added via [extend()][bcql_py.validation.spec.CorpusSpec.extend].
"""
