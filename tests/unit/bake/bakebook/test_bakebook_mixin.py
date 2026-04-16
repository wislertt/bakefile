import types

import pytest

from bake import Bakebook, BakebookMixin, Context, command
from tests.unit.bake.bakebook.utils import ExpectedCommand, assert_commands


def test_mixin_fields_accessible() -> None:
    class ServiceMixin(BakebookMixin):
        service_name: str = "my-service"

    class MyBakebook(ServiceMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    assert bakebook.service_name == "my-service"


def test_multiple_mixins() -> None:
    class EnvMixin(BakebookMixin):
        env: str = "dev"

    class RegionMixin(BakebookMixin):
        region: str = "us-central1"

    class MyBakebook(EnvMixin, RegionMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    assert bakebook.env == "dev"
    assert bakebook.region == "us-central1"


def test_mixin_with_command() -> None:
    class DeployMixin(BakebookMixin):
        deploy_env: str = "staging"

        @command()
        def deploy(self) -> str:
            return f"deploying to {self.deploy_env}"

    class MyBakebook(DeployMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    assert bakebook.deploy() == "deploying to staging"

    assert_commands(
        bakebook,
        {
            "deploy": ExpectedCommand(
                name="deploy", command_type=types.MethodType, output="deploying to staging"
            ),
        },
    )


def test_multiple_mixins_with_commands() -> None:
    class BuildMixin(BakebookMixin):
        @command()
        def build(self) -> str:
            return "built"

    class TestMixin(BakebookMixin):
        @command()
        def test(self) -> str:
            return "tested"

    class MyBakebook(BuildMixin, TestMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    assert bakebook.build() == "built"
    assert bakebook.test() == "tested"

    assert_commands(
        bakebook,
        {
            "build": ExpectedCommand(name="build", command_type=types.MethodType, output="built"),
            "test": ExpectedCommand(name="test", command_type=types.MethodType, output="tested"),
        },
    )


def test_mixin_fields_overridable() -> None:
    class EnvMixin(BakebookMixin):
        env: str = "dev"

    class MyBakebook(EnvMixin, Bakebook):
        pass

    bakebook = MyBakebook(env="prod")
    assert bakebook.env == "prod"


def test_mixin_with_bakebook_subclass() -> None:
    class BaseBakebook(Bakebook):
        base_field: str = "base"

        @command()
        def base_cmd(self) -> str:
            return f"base: {self.base_field}"

    class ServiceMixin(BakebookMixin):
        service: str = "api"

    class FinalBakebook(ServiceMixin, BaseBakebook):
        pass

    bakebook = FinalBakebook()
    assert bakebook.base_field == "base"
    assert bakebook.service == "api"

    assert_commands(
        bakebook,
        {
            "base_cmd": ExpectedCommand(
                name="base_cmd", command_type=types.MethodType, output="base: base"
            ),
        },
    )


def test_mixin_mro_order() -> None:
    class LeftMixin(BakebookMixin):
        value: str = "left"

    class RightMixin(BakebookMixin):
        value: str = "right"

    class MyBakebook(LeftMixin, RightMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    assert bakebook.value == "left"


def test_mixin_without_bakebook_raises() -> None:
    class BadMixin(BakebookMixin):
        field: str = "bad"

    with pytest.raises(TypeError, match="BakebookMixin can only be used with Bakebook subclasses"):
        BadMixin()


def test_mixin_ctx_returns_context(mock_ctx: Context) -> None:
    class MyMixin(BakebookMixin):
        pass

    class MyBakebook(MyMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    with mock_ctx:
        result = bakebook.ctx
        assert result is mock_ctx
        assert isinstance(result, Context)


def test_mixin_ctx_raises_without_click_context() -> None:
    class MyMixin(BakebookMixin):
        pass

    class MyBakebook(MyMixin, Bakebook):
        pass

    bakebook = MyBakebook()
    from bake.utils.exceptions import ContextNotAvailableError

    with pytest.raises(ContextNotAvailableError, match="Command context not available"):
        _ = bakebook.ctx
