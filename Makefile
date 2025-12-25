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
	uv run ruff format --exit-non-zero-on-format .
	uv run ruff check --fix --exit-non-zero-on-fix .
	uv run ty check --error-on-warning

update:
	uv lock --upgrade
	uv sync
	make install-local-deps # only for debugging

pipx-install-bake-test:
	pipx install "bakefile" \
		--index-url https://test.pypi.org/simple/ \
		--pip-args="--pre --extra-index-url https://pypi.org/simple" \
		--force

pipx-install-bake:
	pipx install bakefile --force

install-local-deps:
	uv pip install -e ../typer
	uv pip install -e ../click
