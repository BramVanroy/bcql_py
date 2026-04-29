---
title: BCQL Validator
emoji: 🔎
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: "6.13.0"
app_file: app.py
pinned: false
license: apache-2.0
short_description: Validate BlackLab Corpus Query Language queries.
---

# BCQL Validator (Gradio demo)

A small Gradio app that demonstrates [`bcql_py`](https://github.com/BramVanroy/bcql_py):
parse a BCQL query, validate it against a built-in or custom `CorpusSpec`, and
inspect the resulting AST.

The hosted demo lives at
[huggingface.co/spaces/BramVanroy/bcql_py_validation](https://huggingface.co/spaces/BramVanroy/bcql_py_validation).

## Run locally

From the repository root:

```sh
uv sync --group app
uv run python app/app.py
```

Then open the URL printed in the terminal (default
[http://localhost:7860](http://localhost:7860)).

## Files

- [`app.py`](app.py) - Gradio Blocks app and validation logic.
- [`requirements.txt`](requirements.txt) - Pinned dependencies used by Hugging
  Face Spaces. Local development should use `uv sync --group app` instead so
  that the in-repo source of `bcql_py` is used.
