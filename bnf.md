# Blacklab Corpus Query Language in Backus-Naur Form

As I dug into which parser "paradigm" to use, I found that a recurisve descent parser made much sense for BCQL. Starting from lowest precedence construction down to the highest. I've always been a sucker for recursion (though admittedly I never held much love for Prolog).

Reading into recursive descent parsers more, I got much inspiration from Jamis Buck's [blog post on recursive descent parsers](https://weblog.jamisbuck.org/2015/7/30/writing-a-simple-recursive-descent-parser.html). The first thing to do, he illustrates, is to convert your grammar into [Backus-Naur Form](https://cs61a.org/study-guide/bnf/0) (BNF). In practice I am using EBNF (Extended BNF) which has some nice shorthands like quantifiers `*`.

Let's see if writing this BNF helps me out.

## Terminals

```
STRING          "…" | l"…"
IDENT(IFIER)    [a-zA-Z_]\w*
INT             -?[0-9]+
ARROW           -type->field
ROOT            ^-type->
ALIGN           =type=>field?
FILTER          within | containing | overlap
CMP             = | != | < | <= | > | >=
```

### 1. Sequence-level grammar (outside [...])

```
query          := global_cst EOF

global_cst     := pos_filter
                | pos_filter '::' cc_expr

pos_filter     := rel_align
                | pos_filter FILTER rel_align

rel_align      := union_int
                | union_int arrows
                | union_int aligns

arrows         := arrow_child
                | arrow_child ';' arrows
arrow_child    := ARROW union_int
                | '!' ARROW union_int

aligns         := ALIGN union_int
                | ALIGN union_int ';' aligns

union_int      := sequence
                | union_int ('|' | '&') sequence

sequence       := capture
                | capture sequence

capture        := span
                | IDENT ':' capture

span           := repetition
                | '<' tag_name attr* '/>'
                | '<' tag_name attr* '>'
                | '</' tag_name '>'

repetition     := atom
                | repetition quantifier

quantifier     := '+' | '*' | '?'
                | '{' INT '}'
                | '{' INT ',' INT? '}'

atom           := '[' token_expr? ']'
                | STRING
                | '_'
                | '(' global_cst ')'
                | '!' atom
                | ROOT union_int
                | lookaround
                | IDENT '(' arg_list ')'

lookaround     := ('(?=' | '(?!')  global_cst ')'
                | ('(?<=' | '(?<!') global_cst ')'

arg_list       := ε
                | arg (',' arg)*
arg            := global_cst
                | INT

tag_name       := IDENT | STRING
attr           := IDENT '=' STRING
```

### 2. Token-constraint grammar (inside [...])

```
token_expr     := token_bool

token_bool     := token_not
                | token_bool ('|' | '&') token_not

token_not      := token_cmp
                | '!' token_not

token_cmp      := IDENT ('=' | '!=') STRING
                | IDENT '=' 'in' '[' INT ',' INT ']'
                | IDENT '(' string_list ')'
                | '(' token_bool ')'

string_list    := ε
                | STRING (',' STRING)*
```

### 3. Capture-constraint grammar (after ::)

```
cc_expr        := cc_or_impl

cc_or_impl     := cc_and
                | cc_or_impl ('|' | '->') cc_and

cc_and         := cc_not
                | cc_and '&' cc_not

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