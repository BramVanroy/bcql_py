"""Advanced: spans, relations, and complex queries.

Demonstrates parsing of span queries, position filters, repetition, grouping, unions,
negation, and other advanced BCQL features. Corpus-schema validation is not yet available
in ``bcql_py`` (see README.md TODO), so these examples use only ``parse``.
"""

from bcql_py import parse


print("=== Span queries ===")

# Match-all within a sentence
ast = parse("<s/>")
print(f"  Whole span:   {ast.to_bcql()}")

# Sentence start/end
ast = parse("<s> [] </s>")
print(f"  Start/end:    {ast.to_bcql()}")

# Named entity with attribute
ast = parse('<ne type="PER"/>')
print(f"  NE with attr: {ast.to_bcql()}")


print("\n=== Position filters ===")

ast = parse('"baker" within <s/>')
print(f"  within:     {ast.to_bcql()}")

ast = parse('<s/> containing "baker"')
print(f"  containing: {ast.to_bcql()}")

ast = parse('[pos="N"] within <ne type="PER"/>')
print(f"  combined:   {ast.to_bcql()}")


print("\n=== Repetition and grouping ===")

ast = parse('[pos="ADJ"]+')
print(f"  One-or-more: {ast.to_bcql()}")

ast = parse('[pos="ADJ"]{2,4}')
print(f"  Range:       {ast.to_bcql()}")

ast = parse('([pos="DET"] [pos="ADJ"]* [pos="N"])')
print(f"  Group:       {ast.to_bcql()}")


print("\n=== Unions ===")

ast = parse('[pos="N"] | [pos="V"]')
print(f"  Union: {ast.to_bcql()}")


print("\n=== Negation ===")

ast = parse('[word="the" & pos!="DET"]')
print(f"  Not-equal:     {ast.to_bcql()}")

ast = parse('![pos="PREP"]')
print(f"  Negated token: {ast.to_bcql()}")


print("\n=== Match-all ===")

ast = parse("[]")
print(f"  Match-all:    {ast.to_bcql()}")

ast = parse('"the" [] "man"')
print(f"  With context: {ast.to_bcql()}")


print("\n=== Relations ===")

ast = parse("_ -nmod-> _")
print(f"  Root relation: {ast.to_bcql()}")

ast = parse("A:[]* -nmod-> B:[]*")
print(f"  Captured:      {ast.to_bcql()}")


print("\n=== Global constraints ===")

ast = parse("A:[] B:[] :: A.lemma = B.lemma")
print(f"  Equality: {ast.to_bcql()}")
