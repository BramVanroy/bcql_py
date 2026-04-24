# Token-based querying

[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) started out as purely a token-based corpus engine. This section covers BCQL's token-based features: matching individual tokens, combining constraints, sequences, repetitions, lookaround, spans, and captures.

## Matching a token

A simple token query looks like this:

```
[word="man"]
```

This finds all occurrences of the word _man_.

Each corpus has a default annotation: usually _word_. Using this fact, the query above can be written more concisely as:

```
"man"
```

!!! note "Quote style"
    In BlackLab's CQL dialect, double and single quotes are interchangeable. We use double quotes throughout this guide.

### Multiple annotations

If your corpus includes per-word annotations such as _lemma_ (the headword) and _pos_ (part-of-speech), you can query those too:

```
[lemma="search" & pos="noun"]
```

This matches _search_ and _searches_ when used as a noun.

### Negation

Use the `!=` operator to match everything except a particular value:

```
[pos != "noun"]
```

### Regular expressions

The strings between quotes are [regular expressions](http://en.wikipedia.org/wiki/Regular_expression). For example, to find _man_ or _woman_:

```
"(wo)?man"
```

To find lemmas starting with _under_:

```
[lemma="under.*"]
```

For a complete overview of the regex flavour used, see [Lucene's regular expression syntax](https://www.elastic.co/guide/en/elasticsearch/reference/current/regexp-syntax.html).

??? details "Escaping and literal strings"
    To match characters with special meaning in a regex (such as `.`), escape them with a backslash:

    ```
    [lemma="etc\."]
    ```

    Alternatively, prefix the string with `l` to treat it as a literal string:

    ```
    [lemma=l'etc.']
    ```

    Note that some unexpected characters may be considered special regex characters, such as `<` and `>`. See the Lucene regex docs for details.

### Matching any token

To match any token regardless of its value, use the match-all pattern (an empty pair of square brackets):

```
[]
```

This is most useful as part of a larger sequence query.

### Case- and diacritics sensitivity

[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) defaults to case- and diacritics-_insensitive_ search, so `"panama"` also finds _Panama_.

To match case-sensitively, prefix the pattern with `(?-i)`:

```
"(?-i)Panama"
```

---

## Sequences

### Simple sequences

Separate token patterns with spaces to match a phrase:

```
"the" "tall" "man"
```

You can mix literal words and constrained tokens:

```
"an?|the" [pos="ADJ"] "man"
```

This matches _a wise man_, _an important man_, _the foolish man_, etc.

Using the match-all pattern for a wildcard position:

```
"an?|the" [] "man"
```

### Repetitions

Use the regular-expression repetition operators on whole tokens:

```
[pos="ADJ"]+ "man"
```

The `+` means "one or more times". `*` means zero or more, `?` means zero or once.

For an exact range:

```
[pos="ADJ"]{2,3} "man"
```

For two or more:

```
[pos="ADJ"]{2,} "man"
```

You can group sequences with parentheses and apply operators to the group:

```
("an?|the"? [pos="NOU"])+
```

### Lookahead and lookbehind

!!! tip "Supported from [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) v4.0"

Just like most regex engines, BCQL supports lookahead and lookbehind assertions. These check context without consuming tokens.

**Positive lookahead**: find _cat_ only if followed by _in the hat_:

```
"cat" (?= "in" "the" "hat")
```

**Positive lookbehind**: find _dog_ only if preceded by _very good_:

```
(?<= "very" "good") "dog"
```

**Negative lookahead**: find _cat_ only if _not_ followed by _call_:

```
"cat" (?! "call")
```

**Negative lookbehind**:

```
(?<! "bad") "dog"
```

---

## Punctuation

When a corpus indexes punctuation as the `punct` property of the following word, finding punctuation after a given word requires a pattern like:

```
"dog" [punct=", *"]
```

Because spaces are also included in `punct`, the regex must account for them.

Starting with [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) 4.0.0, _pseudo-annotations_ simplify this:

```
[word="dog" & punctAfter=","]
```

In special cases where more than one punctuation mark is indexed with a word you may still need a broader pattern:

```
[word="dog" & punctAfter=",.*"]
```

!!! tip "Pseudo-annotations are actually functions"
    `punctAfter` is syntactic sugar for a function call:

    ```
    [ punctAfter(",") ]
    ```

    If a non-existent annotation is referenced in a query, [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) checks whether there is a function with that name that takes a single parameter. You can therefore add your own pseudo-annotations by implementing a `QueryFunction` plugin.

---

## Spans

Corpora may contain _spans_: marked regions of text such as sentences, paragraphs, or named entities. BCQL uses an XML-like syntax to query them, regardless of the actual input format.

### Finding spans

To find all sentence spans:

```
<s/>
```

The forward slash before the closing bracket means "the whole span". Compare with `<s>` (start of span) and `</s>` (end of span).

### Words at the start or end of a span

The first word of each sentence:

```
<s> []
```

Sentences ending in _that_:

```
"that" </s>
```

### Words inside a span

Find the word _baker_ inside a `<person/>` span:

```
"baker" within <person/>
```

To return the whole _person_ span that contains _baker_:

```
<person/> containing "baker"
```

!!! tip "Using a regular expression for the span name"
    Match multiple span types at once with a regex:

    ```
    "baker" within <"person|location" />
    ```

    To match all spans in the corpus:

    ```
    <".+" />
    ```

!!! tip "Capturing overlapping spans"
    To retrieve all spans overlapping each hit (e.g. the sentence, paragraph, and chapter containing the match), use the `with-spans` function:

    ```
    with-spans("baker")
    ```

    Or with an explicit span type and capture name:

    ```
    with-spans("baker", <"person|location" />, "props")
    ```

### Universal operators

`within` and `containing` work with any query:

```
([pos="ADJ"]+ containing "tall") "man"
```

This finds adjective sequences applied to _man_ where at least one adjective is _tall_.

---

## Captures

### Capturing part of the match

Label part of the match as a named group using a colon:

```
"an?|the" A:[pos="ADJ"] "man"
```

The adjective is captured in a group named _A_.

Capture a span of multiple tokens:

```
"an?|the" adjectives:[pos="ADJ"]+ "man"
```

!!! tip "Spans are captured automatically"
    If your query involves a span like `<s/>`, it is automatically captured under the span name (`s` in this case). Override the name with `A:<s/>`.

### Capture constraints (global constraints)

After `::` you can write constraints relating different captured tokens:

```
A:[] "by" B:[] :: A.word = B.word
```

This matches _day by day_, _step by step_, etc.

??? details "Multiple-value annotations and constraints"
    Capture constraints can only access the first value indexed for an annotation. If you need multi-value constraint logic, consider rewriting the query without constraints where possible:

    `A:[word="some"] B:[word="queries"] :: A.lemma="some" & B.lemma="query"` can also be written as:

    `A:[word="some" & lemma="some"] B:[word="queries" & lemma="query"]`

    In other cases, adding extra annotations or using inline tags may help.

### Constraint functions

Special functions are available in capture constraints. For example, enforce token ordering:

```
(<s> containing A:"cat") containing B:"fluffy" :: start(B) < start(A)
```

This finds sentences containing both _cat_ and _fluffy_ and requires that _fluffy_ precedes _cat_.

### Local capture constraints

Constraints can appear inside a parenthesised expression, but must only refer to labels captured within those parentheses:

```
(A:[] "and" B:[] :: A.word = B.word) "again"
```

This matches _over and over again_.
