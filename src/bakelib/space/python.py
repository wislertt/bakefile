from contextlib import suppress
from pathlib import Path

import zerv

from bake import params
from bake.ui.logger import strip_ansi

from .base import BaseSpace
from .utils import VENV_BIN


class PythonSpace(BaseSpace):
    @staticmethod
    def _get_python_version() -> str | None:
        path = Path(".python-version")
        if not path.exists():
            return None
        return path.read_text().strip()

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["python"] = {VENV_BIN}  # local - should be from venv
        tools[".venv/bin/python"] = {VENV_BIN}
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
        verbose: params.VerboseBoolOption = False,
    ) -> None:
        integration_tests_path = "tests/integration/"
        if Path(integration_tests_path).exists():
            tests_path = integration_tests_path
            self._test(tests_paths=tests_path, verbose=verbose)
        else:
            self._command_not_available("test_integration")

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
            self._command_not_available("test_all")

    def setup_tools(self) -> None:
        super().setup_tools()
        self.ctx.run("uv python upgrade")

    def setup_project(self) -> None:
        super().setup_project()
        self.ctx.run("uv sync --all-extras --all-groups --frozen")

    def _update_project(self) -> None:
        super()._update_project()
        self.ctx.run("uv lock --upgrade")
        self.ctx.run("uv sync --all-extras --all-groups")

    def _uv_version(self) -> tuple[str, str]:
        result = self.ctx.run(
            "uv version", stream=False, dry_run=False, echo=False, capture_output=True
        )
        package_name, version = strip_ansi(result.stdout.strip()).split()
        return package_name, version

    def _get_version_from_pyproject_toml(self) -> str:
        return self._uv_version()[1]

    def _get_package_name_from_pyproject_toml(self) -> str:
        return self._uv_version()[0]

    @property
    def _package_name(self) -> str:
        return self._get_package_name_from_pyproject_toml()

    @property
    def _version(self) -> str:
        return self._get_version_from_pyproject_toml()

    @_version.setter
    def _version(self, value: str) -> None:
        self._version_setter(value)

    def _version_setter(self, value: str) -> None:
        with suppress(NotImplementedError):
            super()._version_setter(value)
        self.ctx.run(f"uv version {zerv.render(version=value, output_format='pep440')}")

    def _determine_new_version(
        self,
        version: str | None,
        version_format: zerv.OutputFormat = "pep440",
        schema: zerv.StandardSchema | None = None,
    ) -> str:
        return super()._determine_new_version(
            version=version, version_format=version_format, schema=schema
        )
