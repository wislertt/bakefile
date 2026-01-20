test:
	uv run pytest tests/unit/ \
		--cov=src --cov-report=html \
		--cov-report=term-missing --cov-report=xml

test-integration:
	uv run pytest tests/integration/ -v

test-all:
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
	uv run deptry .

update:
	uv lock --upgrade
	uv sync --all-extras
	# make install-local-deps # only for debugging

pipx-install-bake-test:
	pipx install "bakefile" \
		--index-url https://test.pypi.org/simple/ \
		--pip-args="--pre --extra-index-url https://pypi.org/simple" \
		--force

pipx-install-bake:
	pipx install bakefile --force

pipx-install-bake-local:
	uv version $$(zerv flow --output-format pep440)
	pipx install . --force
	uv version 0.0.0

install-local-deps:
	uv pip install -e ../typer
	uv pip install -e ../click

clean:
	git clean -fdX

uvx-install-bake:
	uv tool install bakefile --reinstall


uvx-install-bake-test:
	uv tool install bakefile \
		--index-url https://test.pypi.org/simple/ \
		--extra-index-url https://pypi.org/simple \
		--prerelease allow \
		--reinstall \
		--index-strategy unsafe-best-match

uvx-install-bake-local:
	uv version $$(zerv flow --output-format pep440)
	uv tool install -e . --reinstall --force
	uv version 0.0.0


# uv-all-local
# uv add /Users/wisl/Desktop/vault/personal-repo/bakefile --script bakefile.py
