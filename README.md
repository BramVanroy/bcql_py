# A Python parser for Blacklab Corpus Query Language

## Notes

### ANTLR to generate the needed tools

Blacklab uses ANTLR to generate the parser/lexer in Java based on a [g4 file](https://github.com/instituutnederlandsetaal/BlackLab/blob/e248fc2acf2b8cf44deb2564e8b24138b140d4ca/query-parser/src/main/antlr4/nl/inl/blacklab/queryParser/corpusql/Bcql.g4#L1-L97). We could similarly generate Python files. However, after trying it out, I find the files obfuscated and unclear and I'm not fond of requiring an extra external library. That is not a slight to ANTLR; I am simply not familiar with the tool - I am sure it is incredibly powerful and useful if you know how to use it. To keep a clearer view of this library I therefore strive to make a Python-native implementation that is true to spec. It's also just a fun project that I do not wish to "automate away" (though I might regret that later). At a later time (TODO) I might implement functionality to cross-validate our implementation with the generated ANTLR parser and lexer. For now I will be satisfied with high coverage testing.

If you'd like to try the Python route yourself, you can try it as follows:

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

## Acknowledegments

- [Blacklab](https://blacklab.ivdnt.org/)
- Robert Nystrom's guide on ["Crafting Interpreters"](https://craftinginterpreters.com/scanning.html), specifically the part on "Scanning". Token types and error handling in `bcql_py` is heavily inspired by his work.
