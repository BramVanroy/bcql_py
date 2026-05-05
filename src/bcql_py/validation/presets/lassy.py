"""Lassy / Alpino preset derived from the ``alpino_ds`` DTD.

See the [alpino guide](https://www.let.rug.nl/~vannoord/Lassy/sa-man_lassy.pdf),
Figures 1.1 and 1.2 on pages 13-14.

Based on this this preset describes:

- The full Alpino relation inventory (``rel``), also exposed as
  ``LASSY_RELATION_LABELS`` and integrated as [CorpusSpec.allowed_relations][bcql_py.validation.spec.CorpusSpec.allowed_relations].
- Phrasal categories (``cat``), part-of-speech tags (``pt``), and morphosyntactic
  features (``ntype``, ``getal``, ``graad``, ...).
- Open-string annotations (``word``, ``lemma``, ``postag``, plus identifier / position fields).
- The DTD element names as [CorpusSpec.allowed_span_tags][bcql_py.validation.spec.CorpusSpec.allowed_span_tags], for corpora
  that expose ``alpino_ds`` / ``node`` as XML spans.

Note that "pos" and "root" are excluded, as per the documentation:

> De attributen pos en root representeren de door Alpino gebruikte POSTAG en
ROOT waardes. Deze worden hier niet afzonderlijk gedocumenteerd, en zijn geen
officieel onderdeel van de annotatie.
"""

from __future__ import annotations

from bcql_py.validation.spec import CorpusSpec


LASSY_RELATION_LABELS: frozenset[str] = frozenset(
    {
        "--",
        "app",
        "body",
        "cmp",
        "cnj",
        "crd",
        "det",
        "dlink",
        "dp",
        "hd",
        "hdf",
        "ld",
        "me",
        "mod",
        "mwp",
        "nucl",
        "obcomp",
        "obj1",
        "obj2",
        "pc",
        "pobj1",
        "predc",
        "predm",
        "rhd",
        "sat",
        "se",
        "su",
        "sup",
        "svp",
        "tag",
        "top",
        "vc",
        "whd",
    }
)

LASSY_CAT_LABELS: frozenset[str] = frozenset(
    {
        "advp",
        "ahi",
        "ap",
        "conj",
        "cp",
        "detp",
        "du",
        "inf",
        "mwu",
        "np",
        "oti",
        "pp",
        "ppart",
        "rel",
        "smain",
        "ssub",
        "sv1",
        "svan",
        "ti",
        "top",
        "whq",
        "whrel",
        "whsub",
    }
)

LASSY_PT_LABELS: frozenset[str] = frozenset(
    {
        "adj",
        "bw",
        "let",
        "lid",
        "n",
        "spec",
        "tsw",
        "tw",
        "vg",
        "vnw",
        "vz",
        "ww",
    }
)

LASSY_FEATURE_VALUES: dict[str, frozenset[str]] = {
    "dial": frozenset({"dial"}),
    "ntype": frozenset({"soort", "eigen"}),
    "getal": frozenset({"getal", "ev", "mv"}),
    "graad": frozenset({"basis", "comp", "sup", "dim"}),
    "genus": frozenset({"genus", "zijd", "masc", "fem", "onz"}),
    "naamval": frozenset({"stan", "nomin", "obl", "bijz", "gen", "dat"}),
    "positie": frozenset({"prenom", "nom", "postnom", "vrij"}),
    "buiging": frozenset({"zonder", "met-e", "met-s"}),
    "getal-n": frozenset({"zonder-n", "mv-n"}),
    "wvorm": frozenset({"pv", "inf", "od", "vd"}),
    "pvtijd": frozenset({"tgw", "verl", "conj"}),
    "pvagr": frozenset({"ev", "mv", "met-t"}),
    "numtype": frozenset({"hoofd", "rang"}),
    "vwtype": frozenset(
        {
            "pr",
            "pers",
            "refl",
            "recip",
            "bez",
            "vb",
            "vrag",
            "betr",
            "excl",
            "aanw",
            "onbep",
        }
    ),
    "pdtype": frozenset({"pron", "adv-pron", "det", "grad"}),
    "persoon": frozenset(
        {"persoon", "1", "2", "2v", "2b", "3", "3p", "3m", "3v", "3o"}
    ),
    "status": frozenset({"vol", "red", "nadr"}),
    "npagr": frozenset(
        {"agr", "evon", "rest", "evz", "mv", "agr3", "evmo", "rest3", "evf"}
    ),
    "lwtype": frozenset({"bep", "onbep"}),
    "vztype": frozenset({"init", "versm", "fin"}),
    "conjtype": frozenset({"neven", "onder"}),
    "spectype": frozenset(
        {
            "afgebr",
            "onverst",
            "vreemd",
            "deeleigen",
            "meta",
            "comment",
            "achter",
            "afk",
            "symb",
            "enof",
        }
    ),
    "rel": LASSY_RELATION_LABELS,
    "cat": LASSY_CAT_LABELS,
    "pt": LASSY_PT_LABELS,
}

# Note that POSTAG is free-form but in reality it is a short-hand that combines multiple features (p. 16):
"""
postag="VNW(aanw,det,stan,nom,met-e,mv-n)"
=
pt="vnw"
vwtype="aanw"
pdtype="det"
naamval="stan"
positie="nom"
buiging="met-e"
getal-n="mv-n"
"""
LASSY_OPEN_ATTRIBUTES: frozenset[str] = frozenset(
    {"word", "lemma", "postag", "id", "index", "begin", "end"}
)

LASSY_SPAN_TAGS: frozenset[str] = frozenset(
    {"alpino_ds", "node", "sentence", "comments", "comment"}
)

LASSY = CorpusSpec(
    open_attributes=LASSY_OPEN_ATTRIBUTES,
    closed_attributes=LASSY_FEATURE_VALUES,
    allowed_span_tags=LASSY_SPAN_TAGS,
    allowed_relations=LASSY_RELATION_LABELS,
)
