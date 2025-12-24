test:
	uv run pytest tests/ \
		--cov=src --cov-report=html \
		--cov-report=term-missing --cov-report=xml

lint:
	bunx prettier@latest --write "**/*.{ts,tsx,css,json,yaml,yml,md}"
	uv run toml-sort \
		--sort-inline-arrays --in-place \
		--sort-first=project,dependency-groups \
		pyproject.toml
	uv run ruff check --fix --exit-non-zero-on-fix .
	uv run ruff format --exit-non-zero-on-format .
	uv run ty check --error-on-warning

update:
	uv lock --upgrade
	uv sync
