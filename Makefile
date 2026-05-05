quality:
	uv run interrogate -vv
	uv run ruff check src/bcql_py tests/ scripts/ examples/ generate_llms_file.py
	uv run ruff format --check src/bcql_py tests/ scripts/ examples/ generate_llms_file.py

style:
	uv run ruff check src/bcql_py tests/ scripts/ examples/ generate_llms_file.py --fix
	uv run ruff format src/bcql_py tests/ scripts/ examples/ generate_llms_file.py

typecheck:
	uv run mypy src/bcql_py tests/ scripts/ examples/ generate_llms_file.py

test:
	uv run pytest --cov=src/bcql_py --cov-report=term-missing

DOCS_BRANCH ?= tmp-gh-pages
DOCS_VERSION ?= 0.3.0
DOCS_ALIAS ?= latest
DOCS_ADDR ?= 127.0.0.1:8000
DOCS_SOURCE_REF ?= main

serve-docs:
	BCQL_PY_DOCS_SOURCE_REF=$(DOCS_SOURCE_REF) uv run mike deploy --branch $(DOCS_BRANCH) --update-aliases $(DOCS_VERSION) $(DOCS_ALIAS)
	uv run mike set-default --branch $(DOCS_BRANCH) $(DOCS_ALIAS)
	uv run mike serve -b $(DOCS_BRANCH) -a $(DOCS_ADDR)

documentation: serve-docs
