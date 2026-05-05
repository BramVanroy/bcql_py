"""Lassy / Alpino preset derived from the ``alpino_ds`` DTD.

See the [Alpino guide](https://www.let.rug.nl/~vannoord/Lassy/sa-man_lassy.pdf),
Figures 1.1 and 1.2 on pages 13-14.

Based on this this preset describes:

- The full Alpino relation inventory (``rel``), also exposed as
  ``LASSY_RELATION_LABELS`` and integrated as allowed relation values.
- Phrasal categories (``cat``), part-of-speech tags (``pt``), and morphosyntactic
  features (``ntype``, ``getal``, ``graad``, ...).
- Open-string annotations (``word``, ``lemma``, ``postag``, plus identifier / position fields).
- The DTD element names as allowed span tags, for corpora
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
"""Lassy/Alpino dependency relation labels (``rel`` attribute).

Wired as allowed relation values in the LASSY preset.
See https://www.let.rug.nl/~vannoord/Lassy/sa-man_lassy.pdf (Figures 1.1-1.2) for reference.
"""

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
"""Lassy phrasal category labels (``cat`` attribute).

Wired as closed attribute values in the LASSY preset.
References the Alpino/Lassy tagset for Dutch phrase structure.
"""

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
"""Lassy part-of-speech tags (``pt`` attribute).

Wired as closed attribute values in the LASSY preset.
Covers Dutch parts-of-speech from the Alpino/Lassy tagset.
"""

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
"""Lassy morphosyntactic features and their allowed values.

Wired as closed attributes in the LASSY preset (e.g., ``ntype``, ``getal``, ``graad``, etc.).
Covers Dutch morphological features from the Alpino/Lassy annotation scheme.
"""

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
"""Open annotations in Lassy/Alpino corpora.

Open attributes are those whose values are not restricted to a fixed set.
Includes token word, lemma, combined POS tag, and position metadata.
"""

LASSY_SPAN_TAGS: frozenset[str] = frozenset(
    {"alpino_ds", "node", "sentence", "comments", "comment"}
)
"""Allowed XML span tag names in Lassy/Alpino corpora.

Wired as allowed span tags in the LASSY preset.
Corresponds to the DTD element names used in Alpino-annotated corpora.
"""

LASSY = CorpusSpec(
    open_attributes=LASSY_OPEN_ATTRIBUTES,
    closed_attributes=LASSY_FEATURE_VALUES,
    allowed_span_tags=LASSY_SPAN_TAGS,
    allowed_relations=LASSY_RELATION_LABELS,
)
"""Lassy/Alpino corpus specification for Dutch.

A ready-made [CorpusSpec][bcql_py.validation.spec.CorpusSpec] for validating BCQL queries against
Lassy/Alpino-annotated Dutch corpora. Includes Alpino POS tags, morphosyntactic features, dependency
relations, DTD span tags, and standard CoNLL-like annotations.

Based on the Alpino/Lassy annotation scheme. See https://www.let.rug.nl/~vannoord/Lassy/
"""
