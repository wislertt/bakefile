from bake import Context, command

from .base import BaseSpace


class PythonSpace(BaseSpace):
    def lint(self, ctx: Context) -> None:
        super().lint(ctx=ctx)

        ctx.run(
            [
                "uv",
                "run",
                "toml-sort",
                "--sort-inline-arrays",
                "--in-place",
                "--sort-first=project,dependency-groups",
                "pyproject.toml",
            ]
        )
        ctx.run(["uv", "run", "ruff", "format", "--exit-non-zero-on-format", "."])
        ctx.run(["uv", "run", "ruff", "check", "--fix", "--exit-non-zero-on-fix", "."])
        ctx.run(["uv", "run", "ty", "check", "--error-on-warning", "."])
        ctx.run(["uv", "run", "deptry", "."])

    # @command(help="Run pytest with coverage")
    def test(self, ctx: Context) -> None:
        ctx.run(
            [
                "uv",
                "run",
                "pytest",
                "tests/",
                "--cov=src",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-report=xml",
            ]
        )

    @command(help="Clean gitignored files and sync dependencies with all extras")
    def setup_dev(self, ctx: Context) -> None:
        # git clean -fdX
        # uv sync --all-extras
        # results = ctx.run("git clean -fdX -n", stream=False)
        # print(results.stdout)
        super().clean(ctx=ctx)
        ctx.run("uv sync --all-extras")
