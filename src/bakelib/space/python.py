from pathlib import Path

from bake import params
from bake.ui.logger import strip_ansi

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

    def lint(self) -> None:
        super().lint()

        self.ctx.run(
            "uv run toml-sort --sort-inline-arrays --in-place "
            "--sort-first=project,dependency-groups pyproject.toml"
        )
        self.ctx.run("uv run ruff format --exit-non-zero-on-format .")
        self.ctx.run("uv run ruff check --fix --exit-non-zero-on-fix .")
        self.ctx.run("uv run ty check --error-on-warning --no-progress .")
        self.ctx.run("uv run deptry .")

    def _test(
        self,
        *,
        tests_paths: str | list[str],
        verbose: bool = False,
        coverage_report: bool = True,
        coverage_path: str = "src",
    ) -> None:
        paths = tests_paths if isinstance(tests_paths, str) else " ".join(tests_paths)

        cmd = f"uv run pytest {paths}"

        if coverage_report:
            cmd += (
                f" --cov={coverage_path} --cov-report=html"
                " --cov-report=term-missing --cov-report=xml"
            )

        if verbose:
            cmd += " -s -v"

        self.ctx.run(cmd)

    def test_integration(
        self,
        verbose: params.verbose_bool = False,
    ) -> None:
        integration_tests_path = "tests/integration/"
        if Path(integration_tests_path).exists():
            tests_path = integration_tests_path
            self._test(tests_paths=tests_path, verbose=verbose)
        else:
            self._no_implementation()

    def test(self) -> None:
        unit_tests_path = "tests/unit/"
        tests_path = unit_tests_path if Path(unit_tests_path).exists() else "tests/"
        self._test(tests_paths=tests_path)

    def test_all(self) -> None:
        unit_tests_path = "tests/unit/"
        if Path(unit_tests_path).exists():
            tests_path = "tests/"
            self._test(tests_paths=tests_path)
        else:
            self._no_implementation()

    def setup_project(self) -> None:
        super().setup_project()
        self.ctx.run("uv sync --all-extras --all-groups --frozen")

    def update(self) -> None:
        super().update()
        self.ctx.run("uv lock --upgrade")
        self.ctx.run("uv sync --all-extras --all-groups")

    def _uv_version(self) -> tuple[str, str]:
        result = self.ctx.run("uv version", stream=False, dry_run=False, echo=False)
        package_name, version = strip_ansi(result.stdout.strip()).split()
        return package_name, version

    def get_version_from_pyproject_toml(self) -> str:
        return self._uv_version()[1]

    def _get_package_name_from_pyproject_toml(self) -> str:
        return self._uv_version()[0]

    def package_name(self) -> str:
        return self._get_package_name_from_pyproject_toml()

    def version(self) -> str:
        return self.get_version_from_pyproject_toml()
