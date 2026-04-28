import pytest
from conftest import json_round_trip_test, round_trip_test


ROUND_TRIP_TESTS = {
    '"the"',
    '"a" [lemma="successful"]',
    '"one" A:[]',
    '"one" A:([]{1,2}) []{1,2}',
    '"two|four"',
    '[lemma="be" & word="are"]',
    '<u/> containing "good"',
    '[word="very"] [word="good"] within <u/>',
    '[word != "abcdefg"]',
    "'find' (?= 'or')",
    "'find' (?! 'That' 'is')",
    "(?<= 'not' 'to' ) 'find'",
    "(?<! 'not' 'to' ) 'find'",
    r"'find' [punctBefore='\(']",
    "A:[] B:[] :: A.lemma = B.lemma",
    "A:[] B:[] :: start(A) < start(B)",
    '"brown"+ ([]* "fox")',
    "_ -nmod-> _",
    "A:[]* -nmod-> B:[]*",
    "A:[]* -nmod-> B:[]* :: A.word > B.word",
    "'noot'+ [word != 'noot']+ group:('aap')+",
    "a:[] 'aap' b:[] :: a.word = b.lemma & a.pos = b.pos",
    "(c:'noot')? a:[] 'aap' b:[] :: c -> (a.word = b.word)",
    "'The' []{1,2} 'fox' []{1, 2} 'over'",
    "with-spans('quick' 'brown')",
    "<'.*'> [] 'lazy|find'",
    "[]{1,2} & 'jumps'",
    "[pos='PD.*']+ '(?i)getal'",
}


@pytest.mark.parametrize("source", ROUND_TRIP_TESTS)
def test_round_trip(source):
    round_trip_test(source)


@pytest.mark.parametrize("source", ROUND_TRIP_TESTS)
def test_json_round_trip(source):
    """JSON serialization must be lossless across the full discriminated union.

    This is the regression net for the ``BCQLNodeUnion`` discriminated union:
    every field annotated with the union must serialize its concrete subclass
    fully (no collapsed ``{}`` from abstract-base annotations) and reconstruct
    to a structurally equal AST when validated back through ``TypeAdapter``.
    """
    json_round_trip_test(source)
