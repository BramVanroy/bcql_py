quality:
	uv run ruff check src/bcql_py tests/
	uv run ruff format --check src/bcql_py tests/

style:
	uv run ruff check src/bcql_py tests/ --fix
	uv run ruff format src/bcql_py tests/
typecheck:
	uv run mypy src/bcql_py tests/
test:
	uv run pytest