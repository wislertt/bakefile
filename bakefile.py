from bake import Context, console
from bakelib import PythonLibSpace

bakebook = PythonLibSpace()


@bakebook.command()
def print(ctx: Context):
    # console.out.print(f"ci={bakebook.ci}")
    # console.out.print(f"github_actions={bakebook.github_actions}")
    console.error("test error message")
    console.warning("test error message")
    console.success("test error message")
    console.out.print("::error::This is error message")
    console.out.print("::warning::This is warning message")
    ctx.run("echo hello", echo_cmd="echo hi")
