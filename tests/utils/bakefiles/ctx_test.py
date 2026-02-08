from bake import Bakebook, Context, command
from bake.ui import console


class CtxTestBakebook(Bakebook):
    @command()
    def verify_ctx(self, ctx: Context) -> None:
        assert ctx is self.ctx
        assert id(ctx) == id(self.ctx)
        assert ctx is not None
        assert self.ctx is not None
        assert isinstance(ctx, Context)
        assert isinstance(self.ctx, Context)

        console.echo("SUCCESS - ctx matches self.ctx")
        console.echo(f"ctx_id: {id(ctx)}, self_ctx_id: {id(self.ctx)}")


bakebook = CtxTestBakebook()
