quality:
	uv run ruff check src/bcql_py tests/ scripts/
	uv run ruff format --check src/bcql_py tests/ scripts/

style:
	uv run ruff check src/bcql_py tests/ scripts/ --fix
	uv run ruff format src/bcql_py tests/ scripts/

typecheck:
	uv run mypy src/bcql_py tests/ scripts/
	
test:
	uv run pytest --cov=src/bcql_py --cov-report=term-missing