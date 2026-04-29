# BCQL syntax cheatsheet

A comprehensive reference for [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/)'s flavour of the Corpus Query Language (BCQL).

!!! warning "Schema-dependent attributes"
    This cheatsheet uses common attribute names (`word`, `lemma`, `pos`) and tag values (`"noun"`, `"ADJ"`) for readability. The exact attributes and values you can query depend entirely on how your corpus was annotated. Your corpus might use `[pos="NOU-C"]` or `[tag="NN"]` instead.

---

## 1. Basic token matching & attributes

BlackLab defaults to **case- and diacritics-insensitive** search.

| Query | Meaning |
|-------|---------|
| `"man"` or `[word="man"]` | Finds all occurrences of the word form _man_ |
| `[lemma="search"]` | Finds all forms of the lemma _search_ (e.g. _search_, _searches_) |
| `[lemma="run" & pos="noun"]` | AND operator: _run_ only when tagged as a noun |
| `[pos != "noun"]` | Negation: all tokens except nouns |
| `[]` | Match-all pattern: matches exactly one of any token |
| `"(?-i)Apple"` | Forces case/diacritics-**sensitive** matching |
| `"e\.g\."` or `l"e.g."` | Literal string: backslash escaping or `l` prefix |

---

## 2. Regular expressions within tokens

| Query | Meaning |
|-------|---------|
| `"man\|woman"` | Matches _man_ or _woman_ |
| `[lemma="under.*"]` | `.*`: any character 0 or more times |
| `[word="a?n"]` | `?`: preceding character is optional |

---

## 3. Sequences, gaps, and repetition

| Query | Meaning |
|-------|---------|
| `"the" "tall" "tree"` | Exact phrase search |
| `"an?\|the" [pos="ADJ"] "man"` | Article + exactly one adjective + _man_ |
| `"make" [] "big"` | Gap of exactly one token |
| `[pos="ADJ"]+` | One or more adjectives |
| `[pos="ADJ"]*` | Zero or more adjectives |
| `[pos="ADJ"]?` | Optional adjective |
| `[]{2,5}` | Gap of 2–5 arbitrary tokens |
| `("the"? [pos="noun"])+` | Sequence of nouns, each optionally preceded by _the_ |

---

## 4. Sequence-level logic & filtering

| Query | Meaning |
|-------|---------|
| `"happy" "dog" \| "sad" "cat"` | OR at sequence level |
| `("double" [] & [] "trouble")` | AND at sequence level: intersection (yields _double trouble_) |

---

## 5. Context, lookarounds & punctuation

| Query | Meaning |
|-------|---------|
| `"cat" (?= "in" "the" "hat")` | Positive lookahead |
| `(?<= "very" "good") "dog"` | Positive lookbehind |
| `"cat" (?! "call")` | Negative lookahead |
| `(?<! "bad") "dog"` | Negative lookbehind |
| `[word="dog" & punctAfter=","]` | _dog_ immediately followed by a comma (pseudo-annotation) |
| `meet("cat", "fluffy", 5)` | _cat_ within 5 tokens of _fluffy_ |

---

## 6. XML elements and spans

| Query | Meaning |
|-------|---------|
| `<s/>` | Whole sentence spans |
| `<s>` / `</s>` | Start / end position of a span |
| `"baker" within <person/>` | _baker_ inside a `<person>` span |
| `<person/> containing "baker"` | Entire `<person>` span containing _baker_ |
| `<"person\|location"/>` | Span matching a regex on the tag name |
| `([pos="ADJ"]+ containing "tall") "man"` | Adjective sequence containing _tall_, followed by _man_ |

---

## 7. Captures and global constraints

| Query | Meaning |
|-------|---------|
| `A:[pos="ADJ"]` | Capture the matched adjective as group _A_ |
| `A:[] "by" B:[] :: A.word = B.word` | Global constraint: _A_ and _B_ must be the same word |
| `<s/> containing A:[] []* B:[] :: A.word = "fluffy" & B.word = "cat"` | Both words occur in the sentence in that order |

---

## 8. Relations querying

!!! tip "Supported from BlackLab v4.0"

| Query | Meaning |
|-------|---------|
| `_ -obj-> _` | Any object relation |
| `_ -obj-> "cat"` | Object relation where target is _cat_ |
| `_ -subj-> _ ; -obj-> _` | Same source has both a subject and an object |
| `_ !-obj-> "dog"` | Source has no object relation with target _dog_ |
| `^--> "have"` | Root relation pointing to _have_ |
| `(_ -amod-> "fluffy") -subj-> _` | Multi-level relation chain |
| `rspan(_ -amod-> _, "full")` | Full span covering source and target of `amod` |
| `rcapture(<s/>)` | Capture all relations within the matched sentence |

---

## 9. Parallel corpora querying

!!! tip "Supported from BlackLab v4.0"

| Query | Meaning |
|-------|---------|
| `"cat" ==>nl _` | English _cat_ with its Dutch alignment |
| `"cat" ==>nl? _` | Same, but alignment is optional |
| `"fluffy" ==>nl "pluizig"` | English _fluffy_ aligned to Dutch _pluizig_ |
| `w1:"cat" ==>nl w2:_` | Capture source as `w1`, target as `w2` |
| `rfield("cat" ==>nl _, "nl")` | Return only hits from the Dutch field |
