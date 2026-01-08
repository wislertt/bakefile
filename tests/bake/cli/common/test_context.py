import typer

from bake import Context


class TestContext:
    def test_context_inherits_typer_context(self) -> None:
        """Context should inherit from typer.Context."""
        assert issubclass(Context, typer.Context)

    def test_context_obj_type_annotation(self) -> None:
        """Context.obj should be annotated as BakefileObject."""
        # This is a type-check test; at runtime we verify the annotation exists
        assert hasattr(Context, "__annotations__")
        assert "obj" in Context.__annotations__
