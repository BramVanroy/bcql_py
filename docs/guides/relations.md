# Relations querying

!!! tip "Supported from [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) v4.0"
    Indexing and searching relations requires BlackLab 4.0 or later.

Relations describe how (groups of) words are related to one another. The most common type is the _dependency relation_, which encodes grammatical dependency between words.

Querying relations makes it much easier to find non-adjacent related words, or two related words regardless of word order.

!!! tip "Treebank systems"
    [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) supports relations querying, but is not as powerful as a dedicated treebank system. Relations queries can be combined with regular token-level queries.

---

## An example dependency tree

The examples in this guide are based on the phrase _I have a fluffy cat_:

```
      |
     have
    /    \
 (subj)   (obj)
 /          \
I            cat
           /   |
        (det)(amod)
        /      |
       a     fluffy
```

---

## Finding specific relation types

To find all object relations:

```
_ -obj-> _
```

The `_` marker means "any span, regardless of content". This query matches the span covering both ends of the relation (i.e. _have … cat_), with the relation details returned in match info under the name _obj_.

To restrict the target:

```
_ -obj-> "cat"
```

??? details "Can I use `[]` instead of `_`?"
    In a relation expression, `_` is equivalent to `[]*` (zero or more tokens with no restrictions), which is the correct meaning for "any source or target span". You can write `[]` instead if you know the source and target are always single tokens, but it is slightly slower (BlackLab must verify the length constraint). Stick with `_` for clarity and performance.

---

## A note on terminology

| Context                   | Terms                |
|---------------------------|----------------------|
| Dependency relations      | `head → dependent`   |
| Relations in BlackLab     | `source → target`    |
| Searching tree structures | `parent → child`     |

---

## Finding relation types using regular expressions

The relation type can be a regular expression. To find both subject and object relations:

```
_ -subj|obj-> _
```

or:

```
_ -.*bj-> _
```

Parentheses are optional but can improve readability:

```
_ -(subj|obj)-> _
```

??? details "Relation classes"
    When indexing relations in [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/), you assign each relation a _class_: a short string indicating the family of relations it belongs to. For example, you might assign class `dep` to dependency relations, making an `obj` relation become `dep::obj`.

    `rel` is the default relation class. If you index relations without a class, they automatically get this class. Correspondingly, when searching without specifying a class, `rel::` is prepended to the relation type. If you're not using multiple relation classes, you can ignore this entirely.

---

## Root relations

A dependency tree has a single root relation: a special relation with only a target and no source. Its type is usually called _root_. In the example tree, the root points to _have_.

Find all root relations:

```
^--> _
```

Find root relations pointing to a specific word:

```
^--> "have"
```

---

## Finding two relations with the same source

To find the subject and object of the same verb, use a semicolon to separate _child constraints_:

```
_ -subj-> _ ;
  -obj-> _
```

The source is specified only once. The query finds the entire span covering both relations (i.e. _I have a fluffy cat_ in the example), with both relations returned in match info.

??? details "Target constraint uniqueness"
    When matching multiple relations with the same source, BlackLab enforces that each target constraint matches a distinct relation. Two child constraints will never match the same relation.

---

## Negative child constraints

Prefix the relation operator with `!` to require that a relation does _not_ exist:

```
_  -subj-> _ ;
  !-obj-> "dog"
```

This differs from:

```
_  -subj-> _ ;
   -obj-> [word != "dog"]
```

The second form requires an object relation to exist (with a target that is not _dog_). The first form only requires there is no object relation whose target is _dog_: the verb may have no object at all.

---

## Searching over multiple levels in the tree

Chain the relation operator for multi-level queries:

```
_ -subj-> _ -amod-> "fluffy"
```

Combine multiple levels with multiple child constraints (parentheses required to remove ambiguity):

```
_ -subj-> (_ -amod-> _) ;
  -obj-> _
```

The value of `(_ -amod-> _)` is the _source_ of the `amod` relation, which becomes the target of the `subj` relation.

`-..->` is right-associative, but parentheses are needed here because the parent of `-obj->` would otherwise be ambiguous.

---

## Limitation: descendant search

One current limitation compared to dedicated treebank systems is the absence of support for finding descendants that are not direct children.

The following does **not** work:

```
^--> "have" -->> -amod-> "fluffy"   # NOT SUPPORTED
```

Instead, you must specify the exact number of intervening nodes:

```
^--> "have" --> _ -amod-> "fluffy"
```

A workaround using a hybrid of token-level and relations querying:

```
(<s/> containing (^--> "have")) containing (_ -amod-> "fluffy")
```

---

## Advanced features

### Controlling the result span

By default, a relation expression returns its _source_ span. Use `rspan` to return a different part:

```
rspan(_ -amod-> _, "target")    -- the target token
rspan(_ -amod-> _, "full")      -- the full span covering source and target
rspan(_ -amod-> _)              -- same as "full" (the default)
```

`rspan` also supports `"all"`, which covers all relations matched in a complex query:

```
rspan(_ -subj-> (_ -amod-> _) ; -obj-> _, "all")
```

When using [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) Server, you can also add the URL parameter `adjusthits=true` instead of wrapping in `rspan`.

### Capturing all relations in a span

To capture all relations in the sentence containing a match:

```
"elephant" within rcapture(<s/>)
```

With a custom capture name and relation-type filter:

```
"elephant" within rcapture(<s/>, "relations", "fam::.*")
```

### Cross-field relations

A corpus with multiple annotated fields (e.g. `contents__original` and `contents__corrected`) can have cross-field relations:

```
"mistpyed" -->corrected "mistyped"
```

The target version is appended to the relation operator. Cross-field relations are the foundation for [parallel corpus querying](parallel.md).
