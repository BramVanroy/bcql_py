# Blacklab Corpus Query Language in Backus-Naur Form

As I dug into which parser "paradigm" to use, I found that a recurisve descent parser made much sense for BCQL. Starting from lowest precedence construction down to the highest. I've always been a sucker for recursion (though admittedly I never held much love for Prolog).

Reading into recursive descent parsers more, I got much inspiration from Jamis Buck's [blog post on recursive descent parsers](https://weblog.jamisbuck.org/2015/7/30/writing-a-simple-recursive-descent-parser.html). The first thing to do, he illustrates, is to convert your grammar into [Backus-Naur Form](https://cs61a.org/study-guide/bnf/) (BNF). In practice I am using EBNF (Extended BNF) which has some nice shorthands like quantifiers `*`.

Let's see if writing this BNF helps me out.

## Terminals

The lexer emits these token types. Where the grammar writes a quoted literal (e.g. `'['`, `'->'`), the parser matches the corresponding `TokenType`.

```
STRING          "..." | '...'           -> TokenType.STRING
LITERAL_STRING  l"..." | l'...'         -> TokenType.LITERAL_STRING
IDENT           [a-zA-Z_][\w-]*     -> TokenType.IDENTIFIER
INT             -?[0-9]+            -> TokenType.INTEGER
UNDERSCORE      _                   -> TokenType.UNDERSCORE
FILTER          within | containing | overlap
CMP             = | != | < | <= | > | >=
```

**Note on STRING vs LITERAL_STRING**: Throughout the grammar rules below, `STRING` is used as shorthand for *either* `STRING` or `LITERAL_STRING`. The parser maps them to `StringValue(is_literal=True|False, ...)`.

**Note on arrows**: The lexer decomposes relation / alignment arrows into constituent tokens rather than emitting a single compound terminal:

| Surface form | Emitted tokens |
|---|---|
| `-type->field` | `REL_LINE`  `IDENT`?  `REL_ARROW`  `IDENT`? |
| `-->` | `REL_LINE`  `REL_ARROW` |
| `->` (implication) | `REL_ARROW` |
| `^-type->` | `ROOT_REL_CARET`  `REL_LINE`  `IDENT`?  `REL_ARROW` |
| `=type=>field?` | `ALIGN_LINE`  `IDENT`?  `ALIGN_ARROW`  `IDENT`  `QUESTION`? |

### 1. Sequence-level grammar (outside [...])

```
query           := global_cst EOF

global_cst      := pos_filter
                 | pos_filter ('::' cc_expr)*   /* left-assoc, repeating per Bcql.g4 */

pos_filter     := rel_align
                 | rel_align FILTER pos_filter  /* right-recursive per Bcql.g4 */

rel_align       := sequence_bool
                 | sequence_bool child_rel (';' child_rel)*
                 | sequence_bool aligns

/* G4 divergence (intentional): Bcql.g4's `relationType` rule allows mixing DEP_OP and
   ALIGNMENT_OP in the same semicolon chain. We separate child relations (dep arrows)
   from alignments (alignment arrows) into distinct alternatives so that mixed chains
   like `_ -obj-> _ ; ==>nl _` are rejected. More of a semantic thing but useful nonetheless. */

child_rel       := (IDENT ':')? '-' IDENT? '->' IDENT? rel_align   /* right-recursive */
                 | (IDENT ':')? '!' '-' IDENT? '->' IDENT? rel_align

aligns          := align_child
                 | align_child ';' aligns
align_child     := (IDENT ':')? '=' IDENT? '=>' IDENT '?'? rel_align

sequence_bool   := sequence
                 | sequence_bool ('|' | '&' | '->') sequence  /* booleanOperator in Bcql.g4 */

sequence        := capture
                 | capture sequence

capture         := span
                 | IDENT ':' capture

span            := repetition
                 | '!' span                     /* negation wraps repetition per Bcql.g4 */
                 | '<' tag_name attr* '/>'
                 | '<' tag_name attr* '>'
                 | '</' tag_name '>'

repetition      := atom
                 | repetition quantifier

quantifier      := '+' | '*' | '?'
                 | '{' INT '}'
                 | '{' INT ',' INT? '}'
                 | '{' ',' INT '}'              /* bcql_py extension; not in Bcql.g4 */

atom            := '[' token_expr? ']'
                 | STRING
                 | '_'
                 | '(' global_cst ')'
                 | '^' '-' IDENT? '->' rel_align
                 | lookaround
                 | IDENT '(' arg_list ')'

/* G4 divergence (intentional): Bcql.g4 places `rootRelationType` as a standalone alternative
   in `relationQuery` (our `rel_align`). We place it in `atom` instead, which is more permissive:
   it allows root relations inside sequences, boolean combinations, and captures without needing
   parentheses. The capture label (e.g. `A:^-obj-> _`) is naturally handled by the `capture` level
   rather than requiring special-case grammar like G4's `(captureLabel ':')?` prefix. */

lookaround      := ('(?=' | '(?!')  global_cst ')'
                 | ('(?<=' | '(?<!') global_cst ')'

arg_list        := ε
                 | arg (',' arg)*
arg             := global_cst
                 | INT

tag_name        := IDENT | STRING
attr            := IDENT '=' STRING
```

### 2. Token-constraint grammar (inside [...])

```
token_expr     := token_bool

token_bool     := token_not
                | token_bool ('|' | '&' | '->') token_not  /* all same precedence, left-to-right;
                                                               matches booleanOperator in Bcql.g4 */

token_not      := token_cmp
                | '!' token_not

token_cmp      := IDENT CMP STRING
                | IDENT '=' 'in' '[' INT ',' INT ']'
                | IDENT '(' string_list ')'
                | '(' token_bool ')'

string_list    := ε
                | STRING (',' STRING)*
```

### 3. Capture-constraint grammar (after ::)

```
cc_expr        := cc_bool

cc_bool        := cc_not
                | cc_bool ('&' | '|' | '->') cc_not    /* all same precedence, left-to-right;
                                                          '->' is a single REL_ARROW token */

cc_not         := cc_cmp
                | '!' cc_not

cc_cmp         := cc_atom
                | cc_atom CMP cc_atom

cc_atom        := STRING
                | IDENT '.' IDENT
                | IDENT '(' cc_arg_list ')'
                | '(' cc_expr ')'

cc_arg_list    := ε
                | cc_expr (',' cc_expr)*
```