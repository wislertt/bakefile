from pathlib import Path

from bake import Context, params

from .base import BaseSpace, ToolInfo
from .utils import VENV_BIN, get_expected_paths


def _get_python_version() -> str | None:
    path = Path(".python-version")
    if not path.exists():
        return None
    return path.read_text().strip()


class PythonSpace(BaseSpace):
    def _get_tools(self) -> dict[str, ToolInfo]:
        tools = super()._get_tools()
        tools["python"] = ToolInfo(
            version=_get_python_version(),
            expected_paths=list(get_expected_paths("python", {VENV_BIN})),
        )
        return tools

    def lint(self, ctx: Context) -> None:
        super().lint(ctx=ctx)

        ctx.run(
            "uv run toml-sort --sort-inline-arrays --in-place "
            "--sort-first=project,dependency-groups pyproject.toml"
        )
        ctx.run("uv run ruff format --exit-non-zero-on-format .")
        ctx.run("uv run ruff check --fix --exit-non-zero-on-fix .")
        ctx.run("uv run ty check --error-on-warning --no-progress .")
        ctx.run("uv run deptry .")

    def _test(
        self,
        ctx: Context,
        *,
        tests_paths: str | list[str],
        verbose: bool = False,
        coverage_report: bool = True,
    ) -> None:
        paths = tests_paths if isinstance(tests_paths, str) else " ".join(tests_paths)

        cmd = f"uv run pytest {paths}"

        if coverage_report:
            cmd += " --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml"

        if verbose:
            cmd += " -s -v"

        ctx.run(cmd)

    def test_integration(
        self,
        ctx: Context,
        verbose: params.verbose_bool = False,
    ) -> None:
        integration_tests_path = "tests/integration/"
        if Path(integration_tests_path).exists():
            tests_path = integration_tests_path
            self._test(ctx, tests_paths=tests_path, verbose=verbose)
        else:
            self._no_implementation(ctx)

    def test(self, ctx: Context) -> None:
        unit_tests_path = "tests/unit/"
        tests_path = unit_tests_path if Path(unit_tests_path).exists() else "tests/"
        self._test(ctx, tests_paths=tests_path)

    def test_all(self, ctx: Context) -> None:
        unit_tests_path = "tests/unit/"
        if Path(unit_tests_path).exists():
            tests_path = "tests/"
            self._test(ctx, tests_paths=tests_path)
        else:
            self._no_implementation(ctx)

    def setup_project(self, ctx: Context) -> None:
        super().setup_project(ctx=ctx)
        ctx.run("uv sync --all-extras --all-groups --frozen")

    def update(self, ctx: Context) -> None:
        super().update(ctx=ctx)
        ctx.run("uv lock --upgrade")
        ctx.run("uv sync --all-extras --all-groups")
