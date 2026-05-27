from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.core import TyperCommand

from bake import Context
from bake.cli.common.obj import BakefileObject


class TestContext:
    def test_context_inherits_typer_context(self) -> None:
        """Context should inherit from typer.Context."""
        from typer import Context as TyperContext

        assert issubclass(Context, TyperContext)

    def test_context_obj_type_annotation(self) -> None:
        """Context.obj should be annotated as BakefileObject."""
        assert hasattr(Context, "__annotations__")
        assert "obj" in Context.__annotations__


class TestContextProperties:
    """Test Context property delegation to BakefileObject."""

    @pytest.fixture
    def obj(self) -> BakefileObject:
        return BakefileObject(
            chdir=Path("."),
            file_name="bakefile.py",
            bakebook_name="__bakebook__",
            dry_run=True,
            bake_log_verbosity=2,
        )

    @pytest.fixture
    def ctx(self, obj: BakefileObject) -> Context:
        return Context(command=TyperCommand("test"), obj=obj)

    def test_dry_run(self, ctx: Context) -> None:
        assert ctx.dry_run is True

    def test_verbosity(self, ctx: Context) -> None:
        assert ctx.verbosity == 2

    def test_bakebook(self, ctx: Context) -> None:
        assert ctx.bakebook is None


class TestContextRunMethod:
    """Test Context.run() method."""

    @pytest.fixture
    def ctx(self) -> Context:
        obj = BakefileObject(
            chdir=Path("."),
            file_name="bakefile.py",
            bakebook_name="__bakebook__",
            dry_run=True,
        )
        return Context(command=TyperCommand("test"), obj=obj)

    def test_run_injects_dry_run(self, ctx: Context, monkeypatch: pytest.MonkeyPatch) -> None:
        spy_run = MagicMock(return_value=MagicMock())
        monkeypatch.setattr("bake.cli.common.context._run", spy_run)

        ctx.run("echo test")

        spy_run.assert_called_once()
        assert spy_run.call_args.kwargs["dry_run"] is True

    def test_run_script_injects_dry_run(
        self, ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        spy_run_script = MagicMock(return_value=MagicMock())
        monkeypatch.setattr("bake.cli.common.context._run_script", spy_run_script)

        ctx.run_script("Deploy", "echo deploying...")

        spy_run_script.assert_called_once()
        assert spy_run_script.call_args.kwargs["dry_run"] is True
