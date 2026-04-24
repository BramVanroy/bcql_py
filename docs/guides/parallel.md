# Parallel corpus querying

!!! tip "Supported from [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) v4.0"
    Indexing and searching parallel corpora requires BlackLab 4.0 or later.

A _parallel corpus_ contains multiple versions of the same content: typically in different languages or time periods: with alignment information recorded at various levels (paragraph, sentence, word).

Examples: EU Parliament discussions in multiple European languages, or different translations of a classic work such as Homer's _Odyssey_.

[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/)'s parallel corpus functionality uses cross-field relations (see [Relations](relations.md)) to find alignments between content versions.

The alignment operator `==>` captures all relations between a left and right span. It essentially means "capture all alignment relations between (part of) the left and right span".

---

## Basic parallel querying

Suppose your corpus has fields `contents__en` (English) and `contents__nl` (Dutch), and English is the default field. To find the Dutch translation of an English word:

```
"cat" ==>nl _
```

The hit is the English word _cat_. Match info contains a group named `rels` with all alignment relations found (one relation in this case, between _cat_ and its Dutch equivalent). The hit response includes an `otherFields` section with the corresponding Dutch content fragment.

To find alignments at the sentence level:

```
<s/> containing "cat" ==>nl _
```

This finds aligned English and Dutch sentences, including any word-level alignments within those sentences.

??? details "Required versus optional alignment"
    The `==>` operator _requires_ that an alignment exists. To return hits even when no alignment is found on the right side, use `==>nl?` (the `?` makes the alignment optional):

    ```
    "cat" ==>nl? _
    ```

    With `==>nl?`, you see English _cat_ hits both with and without a Dutch alignment. With `==>nl`, only hits where the alignment exists are returned.

---

## Switching the main search field

To search the Dutch field and align with English:

```
"kat" ==>en _
```

But you also need to specify `field=nl` as a [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) Server parameter so that the correct field (`contents__nl`) is used as the main search field. BlackLab automatically recognises that you are specifying a version of the main annotated field.

---

## Filtering the target span

Replace `_` with a token query to constrain the target:

```
"fluffy" ==>nl "pluizig"
```

This only returns hits where the English word _fluffy_ is aligned to exactly the Dutch word _pluizig_.

---

## Multiple alignment queries

Use multiple alignment operators in a single query to match across more than one field:

```
"fluffy" ==>nl "pluizig" ;
         ==>de "flauschig"
```

---

## Filtering by relation type

Just like in other relations queries, you can filter by alignment type:

```
"fluffy" =word=>nl "pluizig"
```

Only relations of type `word` are returned. The relation type also becomes the capture name (`word` instead of the default `rels`).

---

## Renaming the relations capture

Override the default `rels` capture name:

```
<s/> alignments:==>nl _
```

Alignment relations are now captured in a group named `alignments`.

---

## Capturing in target fields

Capture parts of the target query like normal:

```
"and" w1:[] ==>nl "en" w2:[]
```

Match info will contain `w1` (from the English field) and `w2` (from the Dutch field).

---

## `rfield()`: return hits from a target field only

To show only hits from the target field after a parallel query:

```
rfield("fluffy" =word=>nl "pluizig", "nl")
```

This is useful when you want to highlight the contents of one target field rather than the source field.
