# A Python parser for Blacklab Corpus Query Language

## Installation

Not on PyPi yet so clone from Github first:

```sh
git clone https://github.com/BramVanroy/bcql_py.git --depth 1
cd bcql_py
uv sync
```

## Notes

### ANTLR to generate the needed tools

Blacklab uses ANTLR to generate the parser/lexer in Java based on a [g4 file](https://github.com/instituutnederlandsetaal/BlackLab/blob/e248fc2acf2b8cf44deb2564e8b24138b140d4ca/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4#L1-L97). We could similarly generate Python files. However, after trying it out, I find the files obfuscated and unclear and I'm not fond of requiring an extra external library. That is not a slight to ANTLR; I am simply not familiar with the tool - I am sure it is incredibly powerful and useful if you know how to use it. To keep a clearer view of this library I therefore strive to make a Python-native implementation that is true to spec. It's also just a fun project that I do not wish to "automate away" (though I might regret that later). At a later time (TODO) I might implement functionality to cross-validate our implementation with the generated ANTLR parser and lexer. For now I will be satisfied with high coverage testing. In case of doubt I have followed the Bcql.g4 file.

If you'd like to try the ANTLR route yourself, you can try it as follows:

1. Install requirements (not included in our pyproject.toml file, you'll need to download these yourself!)

```sh
uv pip install requests antlr4-tools antlr4-python3-runtime
```

2. Download the Black G4 definition from github. You can optionally specify a `--branch` or `--tag`, defaults to `--branch dev`.

```sh
uv run python scripts/get_bcql_g4.py
# Saved to parser/Bcql.g4
cd parser/
```

3. Run ANTLR (you can update `-v` to [the latest version](https://github.com/antlr/antlr4/releases) if needed)

```sh
antlr4 -v 4.13.2 -Dlanguage=Python3 Bcql.g4
```

### Design choices

Building a lexer is somewhat care-free with the exception of deciding which boundaries to use. As an example, I chose to tokenize the regex positive lookbehind `(?<=` as a single Token but I could have chosen to go deeper and re-use regular parens `(`, followed by a question mark (also used as quantifier) `?`, followed by the single-token `<=`, also used as a mathematical operator. Such changes would make the "vocabulary" smaller but apart from that I did not see much benefit - though I am sure that there are more arguments to make both for and against a minimalist approach.

The parser, however, is a different beast entirely. be separated so we can re-use it and re-use `<=` as a single entity operator), building a parser 

### Pydantic models

#### Model rebuilding

In many of the models in `models/*.py` you will see that that we have to call `model_rebuild` after having set the discirminatory `*ConstraintExpr` union. This union is needed for typing - some of the constraint nodes have operands that can be any constraint nodes (union). Pydantic needs to know about the union after all the individual classes have been defined, so we call `model_rebuild` on all of them at the end of the file.

If we don't do this, we'll get a Pydantic error about the forward reference not being resolved when we try to create a NotConstraint or BoolConstraint

## Acknowledegments

- [Blacklab](https://blacklab.ivdnt.org/)
- Robert Nystrom's guide on ["Crafting Interpreters"](https://craftinginterpreters.com/scanning.html), specifically the part on "Scanning". Token types and error handling in `bcql_py` is heavily inspired by his work.
- Jamis Buck's [blog post on recursive descent parsers](https://weblog.jamisbuck.org/2015/7/30/writing-a-simple-recursive-descent-parser.html)
- Berkeley [course notes on BNF](https://cs61a.org/study-guide/bnf/)

## TODO

- Output AST as eBNF grammar?
- Allow specification of corpus-specific properties for verification: valid XML tags, valid attribute-value pairs (which naturally includes tagset, e.g. `pos=[V,N,ADJ...]`), supported dependency relations, alignment specified or not, etc.