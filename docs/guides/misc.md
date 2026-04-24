# Operator precedence and CQL compatibility

---

## Operator precedence

This is the precedence of [BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/)'s BCQL operators, from highest to lowest. Higher-precedence operators bind more tightly.

### Inside token brackets `[ ]`

| Operator | Description | Associativity |
|----------|-------------|---------------|
| `!` | logical not | right |
| `( )` | function call | left |
| `.` | annotation selector (constraints only) | left |
| `=` `!=` | equals / not equals | left |
| `<` `<=` `>` `>=` | comparison (constraints only) | left |
| `&` `\|` `->` | logical and / or / implication | left |

### At the sequence level (outside token brackets)

| Operator | Description | Associativity |
|----------|-------------|---------------|
| `!` | logical not | right |
| `[ ]` | token brackets | left |
| `( )` | function call | left |
| `*` `+` `?` `{n}` `{n,m}` | repetition | left |
| `:` | capture | right |
| `< />` `< >` `</ >` | span (start / whole / end) | left |
| `[] []` | sequence (implied operator) | left |
| `\|` `&` | union / intersection | left |
| `--> [ ; --> ]` `^-->` `==> [ ; ==> ]` | child relation / root relation / alignment | right |
| `within` `containing` `overlap` | position filter | right |
| `::` | capture constraint | left |

!!! note
    `|` and `&` have the **same** precedence. Do not rely on `&` binding more tightly than `|` (as you might expect from most programming languages).

### Examples

| Query | Interpreted as |
|-------|---------------|
| `[word = "can" & pos != "verb"]` | `[ (word = "can") & (pos != "verb") ]` |
| `[pos = "verb" \| pos = "noun" & word = "can"]` | `[ (pos = "verb" \| pos = "noun") & word = "can" ]` |
| `A:"very"+` | `A:("very"+)` |
| `A:_ --> B:_` | `(A:_) --> (B:_)` |
| `_ -obj-> _ -amod-> _` | `_ -obj-> (_ -amod-> _)` |
| `!"d.*" & ".e.*"` | `(!"d.*") & ".e.*"` → `[word != "d.*" & word = ".e.*"]` |
| `"cow" within <pasture/> containing "grass"` | `"cow" within (<pasture/> containing "grass")` |

Use grouping parentheses `( )` at either level to override precedence.

---

## CQL compatibility

[BlackLab](https://github.com/instituutnederlandsetaal/BlackLab/) supports the core of the [Corpus Query Language](https://cwb.sourceforge.io/files/CQP_Tutorial/) (CQL/CQP) from IMS Corpus Workbench, with some differences.

### Supported features

- Matching on token annotations using regex and `=`, `!=`, `!`. Example: `[word="bank"]` or just `"bank"`.
- Case/accent sensitive matching with `"(?-i)..."`.
- Combining criteria with `&`, `|`, `!`, and parentheses. Example: `[lemma="bank" & pos="V"]`.
- Match-all pattern `[]`. Example: `"a" [] "day"`.
- Repetition operators `+`, `*`, `?`, `{n}`, `{n,m}` at the token level. Example: `[pos="ADJ"]+`.
- Sequences of token constraints. Example: `[pos="ADJ"] "cow"`.
- Sequence operators `|`, `&`, and parentheses. Example: `"happy" "dog" | "sad" "cat"`.
- Tag positions: `<s>` (start), `</s>` (end), `<s/>` (whole span). XML attribute values may be used: `<ne type="PERS"/>`.
- `within` and `containing`. Example: `"you" "are" within <s/>`.
- Named captures and global constraints. Example: `"big" A:[] "or" "small" B:[] :: A.word = B.word`.
- Integer ranges. Example: `[pos="verb" & pos_confidence=in[50,100]]`.

### Differences from CWB / Sketch Engine

| Feature | BlackLab behaviour |
|---------|-------------------|
| Default sensitivity | Case-**insensitive** (CWB/Sketch defaults to case-sensitive) |
| Case-sensitive matching | `"(?-i)..."` or `"(?c)..."` |
| Literal strings | Backslash-escape (`"e\.g\."`) or `l` prefix (`l"e.g."`) |
| XML span syntax | `<s/>`, `<s>`, `<s type="A">`: differs from CWB in attribute syntax |
| Capture constraints | Only literal matching (no regex) after `::` |
| `@` anchor / `target` label | Not supported; use named anchors instead |
| Backreferences in token constraints | Not supported: `A:[] [] [word = A.word]` does not work: use `A:[] [] B:[] :: A.word = B.word` |
| Sequence-level set operators | Use `&`, `\|`, `!` instead of CWB's `intersection`, `union`, `difference` |

### Currently unsupported CWB features

- `lbound` / `rbound` functions (use `<s>` / `</s>` positions instead).
- `distance` / `distabs` functions and `match` / `matchend` anchor points in capture constraints.
- Using an XML element name as a token constraint (e.g. `!np` to mean "not inside an `<np/>` tag").

If a missing feature is important to you, please [open an issue](https://github.com/BramVanroy/bcql-py/issues) or refer to [BlackLab's issue tracker](https://github.com/instituutnederlandsetaal/BlackLab/issues).
