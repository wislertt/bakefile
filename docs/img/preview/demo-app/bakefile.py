from bake import Bakebook, command, console


class MyBakebook(Bakebook):
    @command()
    def build(self) -> None:
        """Build the project."""
        console.echo("Building...")
        self.ctx.run("cargo build")

    @command()
    def test(self) -> None:
        """Run the test suite."""
        console.echo("Testing...")
        self.ctx.run("cargo test")


bakebook = MyBakebook()
