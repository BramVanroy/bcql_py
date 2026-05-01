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

docs:
	uv run mkdocs serve
