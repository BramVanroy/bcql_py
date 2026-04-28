"""Semantic validation tests.

Covers :class:`bcql_py.validation.CorpusSpec`, :func:`bcql_py.validation.validate`,
and the shipped presets. Tests parse real BCQL queries via the public API and
assert on the resulting validation issues rather than poking at private AST
internals; this keeps the tests coupled to observable behavior.
"""

from __future__ import annotations

import pytest

from bcql_py import BCQLValidationError, CorpusSpec, parse, validate
from bcql_py.validation.presets import LASSY, UD


def _pos_spec(tags: set[str]) -> CorpusSpec:
    """Tiny reusable spec: `pos` restricted to the given tag set."""
    return CorpusSpec(closed_attributes={"pos": frozenset(tags)})


def test_empty_spec_accepts_everything():
    ast = parse('[word="hello"] [pos="NOUN"]', spec=CorpusSpec())
    assert ast is not None


def test_strict_attributes_rejects_unknown_annotation():
    spec = CorpusSpec(open_attributes={"word"}, strict_attributes=True)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[lemma="go"]', spec=spec)
    assert excinfo.value.issues[0].kind == "unknown_annotation"
    assert excinfo.value.issues[0].context["annotation"] == "lemma"


def test_non_strict_allows_unknown_annotation():
    spec = CorpusSpec(open_attributes={"word"})
    parse('[lemma="go"]', spec=spec)


def test_closed_attribute_rejects_invalid_literal():
    spec = _pos_spec({"NOUN", "VERB"})
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[pos="BOGUS"]', spec=spec)
    issue = excinfo.value.issues[0]
    assert issue.kind == "invalid_annotation_value"
    assert issue.context["annotation"] == "pos"
    assert issue.context["value"] == "BOGUS"
    assert issue.context["allowed"] == ["NOUN", "VERB"]
    assert issue.context["suggestion"] is None
    assert "Allowed values: NOUN, VERB" in issue.message


def test_closed_attribute_suggests_close_match():
    spec = _pos_spec({"NOUN", "VERB", "ADJ", "ADV"})
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[pos="NOU"]', spec=spec)
    issue = excinfo.value.issues[0]
    assert issue.kind == "invalid_annotation_value"
    assert issue.context["suggestion"] == "NOUN"
    assert "Did you mean 'NOUN'" in issue.message


def test_closed_attribute_accepts_valid_literal():
    parse('[pos="NOUN"]', spec=_pos_spec({"NOUN", "VERB"}))


def test_closed_attribute_skips_regex_values():
    # "NOUN|VERB" is a regex alternation, not a literal: must not be rejected.
    parse('[pos="NOUN|VERB"]', spec=_pos_spec({"NOUN", "VERB"}))


def test_closed_attribute_accepts_literal_prefix():
    # Using the l"..." literal-string prefix should still validate.
    parse('[pos=l"NOUN"]', spec=_pos_spec({"NOUN", "VERB"}))


def test_fail_fast_false_collects_multiple_issues():
    spec = _pos_spec({"NOUN"}).extend(
        open_attributes={"word"}, strict_attributes=True
    )
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[pos="BOGUS"] [lemma="x"]', spec=spec, fail_fast=False)
    kinds = sorted(issue.kind for issue in excinfo.value.issues)
    assert kinds == ["invalid_annotation_value", "unknown_annotation"]


def test_fail_fast_true_raises_on_first_issue():
    spec = _pos_spec({"NOUN"}).extend(
        open_attributes={"word"}, strict_attributes=True
    )
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[pos="BOGUS"] [lemma="x"]', spec=spec, fail_fast=True)
    assert len(excinfo.value.issues) == 1


def test_alignment_disallowed():
    spec = CorpusSpec(allow_alignment=False)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('"a" ==>nl "b"', spec=spec)
    assert excinfo.value.issues[0].kind == "alignment_not_allowed"


def test_alignment_field_restricted():
    spec = CorpusSpec(allowed_alignment_fields={"nl"})
    parse('"a" ==>nl "b"', spec=spec)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('"a" ==>fr "b"', spec=spec)
    assert excinfo.value.issues[0].kind == "unknown_alignment_field"
    assert excinfo.value.issues[0].context["field"] == "fr"


def test_relations_disallowed():
    spec = CorpusSpec(allow_relations=False)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse("_ -nsubj-> _", spec=spec)
    assert excinfo.value.issues[0].kind == "relations_not_allowed"


def test_unknown_relation_type():
    spec = CorpusSpec(allowed_relations={"nsubj", "obj"})
    with pytest.raises(BCQLValidationError) as excinfo:
        parse("_ -bogus-> _", spec=spec)
    assert excinfo.value.issues[0].kind == "unknown_relation_type"


def test_known_relation_passes():
    parse("_ -nsubj-> _", spec=CorpusSpec(allowed_relations={"nsubj"}))


def test_relation_regex_is_skipped():
    # "nsubj|obj" is a regex; validator skips it rather than risk false-positives.
    parse("_ -nsubj|obj-> _", spec=CorpusSpec(allowed_relations={"nsubj"}))


def test_root_relation_checked():
    spec = CorpusSpec(allowed_relations={"root"})
    parse("^-root-> _", spec=spec)
    with pytest.raises(BCQLValidationError):
        parse("^-bogus-> _", spec=spec)


def test_span_tag_restriction():
    spec = CorpusSpec(allowed_span_tags={"s", "p"})
    parse("<s/>", spec=spec)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse("<doc/>", spec=spec)
    assert excinfo.value.issues[0].kind == "unknown_span_tag"


def test_span_attribute_restriction():
    spec = CorpusSpec(
        allowed_span_tags={"ne"},
        allowed_span_attributes={"ne": {"type"}},
    )
    parse('<ne type="PERS"/>', spec=spec)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('<ne lang="en"/>', spec=spec)
    assert excinfo.value.issues[0].kind == "unknown_span_attribute"


def test_merge_unions_sets():
    a = CorpusSpec(open_attributes={"word"}, allowed_relations={"nsubj"})
    b = CorpusSpec(open_attributes={"lemma"}, allowed_relations={"obj"})
    merged = a.merge(b)
    assert merged.open_attributes == frozenset({"word", "lemma"})
    assert merged.allowed_relations == frozenset({"nsubj", "obj"})


def test_merge_preserves_restrictive_flags():
    restrictive = CorpusSpec(allow_alignment=False, allow_relations=False)
    permissive = CorpusSpec()
    merged = restrictive.merge(permissive)
    assert merged.allow_alignment is False
    assert merged.allow_relations is False


def test_extend_unions_closed_values():
    spec = _pos_spec({"NOUN"}).extend(closed_attributes={"pos": {"CUSTOM"}})
    assert "CUSTOM" in spec.closed_attributes["pos"]
    assert "NOUN" in spec.closed_attributes["pos"]


def test_lassy_preset_pt_values():
    parse('[pt="n"]', spec=LASSY)
    parse('[pt="ww"]', spec=LASSY)
    with pytest.raises(BCQLValidationError):
        parse('[pt="NOUN"]', spec=LASSY)


def test_lassy_preset_feature_values():
    parse('[getal="ev"]', spec=LASSY)
    parse('[graad="comp"]', spec=LASSY)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[graad="bogus"]', spec=LASSY)
    ctx = excinfo.value.issues[0].context
    assert ctx["annotation"] == "graad"
    assert ctx["value"] == "bogus"


def test_lassy_preset_relations():
    parse("_ -hd-> _", spec=LASSY)
    parse("_ -obj1-> _", spec=LASSY)
    with pytest.raises(BCQLValidationError):
        parse("_ -nsubj-> _", spec=LASSY)


def test_lassy_preset_open_attributes():
    parse('[word="huis"]', spec=LASSY)
    parse('[lemma="lopen"]', spec=LASSY)


def test_lassy_preset_span_tag():
    parse("<alpino_ds/>", spec=LASSY)
    with pytest.raises(BCQLValidationError):
        parse("<document/>", spec=LASSY)


def test_ud_preset_pos():
    parse('[upos="NOUN"]', spec=UD)
    parse('[pos="VERB"]', spec=UD)
    with pytest.raises(BCQLValidationError):
        parse('[upos="bogus"]', spec=UD)


def test_ud_preset_features():
    parse('[Number="Sing"]', spec=UD)
    parse('[Case="Nom"]', spec=UD)
    parse('[PronType="Prs"]', spec=UD)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[Case="Bogus"]', spec=UD)
    ctx = excinfo.value.issues[0].context
    assert ctx["annotation"] == "Case"
    assert ctx["value"] == "Bogus"


def test_ud_preset_relations():
    parse("_ -nsubj-> _", spec=UD)
    parse("^--> _", spec=UD)
    with pytest.raises(BCQLValidationError):
        parse("_ -boguspocus-> _", spec=UD)


def test_ud_preset_deprel_as_annotation():
    parse('[deprel="nsubj"]', spec=UD)
    with pytest.raises(BCQLValidationError):
        parse('[deprel="bogus"]', spec=UD)


def test_ud_preset_open_attributes():
    parse('[word="run"]', spec=UD)
    parse('[lemma="run"]', spec=UD)
    parse('[xpos="VBZ"]', spec=UD)


def test_ud_preset_subtype_extension():
    spec = UD.extend(allowed_relations={"nsubj:pass", "acl:relcl"})
    parse("_ -nsubj:pass-> _", spec=spec)


def test_validate_function_directly():
    ast = parse('[pos="BOGUS"]')
    with pytest.raises(BCQLValidationError):
        validate(ast, _pos_spec({"NOUN"}))


def test_validate_clean_ast_is_noop():
    ast = parse('[pos="NOUN"]')
    validate(ast, _pos_spec({"NOUN"}))


def test_validation_error_string_representation():
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('[pos="BOGUS"]', spec=_pos_spec({"NOUN"}))
    text = str(excinfo.value)
    assert "BOGUS" in text
    assert "pos" in text


def test_integer_range_unknown_annotation_strict():
    spec = CorpusSpec(open_attributes={"word"}, strict_attributes=True)
    with pytest.raises(BCQLValidationError) as excinfo:
        parse("[confidence=in[50,100]]", spec=spec)
    assert excinfo.value.issues[0].kind == "unknown_annotation"


def test_nested_query_traversal():
    # The validator must descend into groups, sequences, repetitions, captures.
    with pytest.raises(BCQLValidationError) as excinfo:
        parse('A:([pos="BOGUS"]){2}', spec=_pos_spec({"NOUN"}))
    assert excinfo.value.issues[0].kind == "invalid_annotation_value"
