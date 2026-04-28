quality:
	uv run ruff check src/bcql_py tests/ scripts/ examples/
	uv run ruff format --check src/bcql_py tests/ scripts/ examples/

style:
	uv run ruff check src/bcql_py tests/ scripts/ examples/ --fix
	uv run ruff format src/bcql_py tests/ scripts/ examples/

typecheck:
	uv run mypy src/bcql_py tests/ scripts/ examples/

test:
	uv run pytest --cov=src/bcql_py --cov-report=term-missing

docs:
	uv run mkdocs serve
