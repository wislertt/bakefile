from pathlib import Path

from bake import Context, console
from bakelib import PythonLibSpace


class MyBakebook(PythonLibSpace):
    def update(self, ctx: Context) -> None:
        super().update(ctx)

        examples_dir = Path("examples")
        if examples_dir.exists():
            for example_dir in sorted(examples_dir.iterdir()):
                if not example_dir.is_dir():
                    continue
                console.start(f"Updating {example_dir}")
                ctx.run("bake update", cwd=example_dir)

        hooks_dir = Path(".claude/hooks")
        console.start(f"Updating {hooks_dir}")
        ctx.run("npm update --no-progress", cwd=hooks_dir)


bakebook = MyBakebook()


@bakebook.command()
def print1(ctx: Context):
    # console.out.print(f"ci={bakebook.ci}")
    # console.out.print(f"github_actions={bakebook.github_actions}")
    console.error("test error message")
    console.warning("test error message")
    console.success("test error message")
    console.out.print("::error::This is error message")
    console.out.print("::warning::This is warning message")
    console.github_action_add_mask("my-secret-token-123")
    console.out.print("Token: my-secret-token-123")
    ctx.run("echo hello", echo_cmd="echo hi")
