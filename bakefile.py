from pathlib import Path

from bake import Context, console
from bakelib import PythonLibSpace


class MyBakebook(PythonLibSpace):
    def update(self, ctx: Context) -> None:
        super().update(ctx)
        self._update_examples(ctx)
        self._update_hooks(ctx)

    def _update_examples(self, ctx: Context) -> None:
        examples_dir = Path("examples")
        if not examples_dir.exists():
            return

        for example_dir in sorted(examples_dir.iterdir()):
            if not example_dir.is_dir():
                continue
            console.start(f"Updating {example_dir}")
            ctx.run("bake update", cwd=example_dir)

    def _update_hooks(self, ctx: Context) -> None:
        hooks_dir = Path(".claude/hooks")
        console.start(f"Updating {hooks_dir}")
        ctx.run("npm update", cwd=hooks_dir)


bakebook = MyBakebook()
