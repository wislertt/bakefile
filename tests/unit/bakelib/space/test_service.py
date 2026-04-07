import pytest
import typer
from pydantic import ValidationError

from bake import Context
from bakelib.space import params
from bakelib.space.service import BaseServiceSpace


class ConcreteServiceSpace(BaseServiceSpace):
    service_name: str = "test-service"


class FastBuildServiceSpace(BaseServiceSpace):
    service_name: str = "fast-service"

    def build(self, fast: params.FastOption = 0) -> None:
        _ = fast


class TestBareServiceSpace:
    def test_init_raises_without_service_name(self) -> None:
        with pytest.raises(ValidationError):
            BaseServiceSpace()  # ty: ignore[missing-argument]


class TestServiceSpaceInit:
    def test_init_with_service_name(self) -> None:
        space = ConcreteServiceSpace()
        assert space.service_name == "test-service"


class TestBuildCommand:
    def test_build_command_exits_with_code_1(self, mock_ctx: Context) -> None:
        space = ConcreteServiceSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                space.build()
            assert exc_info.value.exit_code == 1


class TestBuildWithFastOverride:
    def test_child_can_add_fast_option(self, mock_ctx: Context) -> None:
        space = FastBuildServiceSpace()
        with mock_ctx:
            space.build(fast=1)  # no error, fast accepted

    def test_child_build_defaults_fast_to_zero(self, mock_ctx: Context) -> None:
        space = FastBuildServiceSpace()
        with mock_ctx:
            space.build()  # fast defaults to 0


class TestDeployCommand:
    def test_deploy_command_exits_with_code_1(self, mock_ctx: Context) -> None:
        space = ConcreteServiceSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                space.deploy()
            assert exc_info.value.exit_code == 1


class TestDestroyCommand:
    def test_destroy_command_exits_with_code_1(self, mock_ctx: Context) -> None:
        space = ConcreteServiceSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                space.destroy()
            assert exc_info.value.exit_code == 1


class TrackingServiceSpace(BaseServiceSpace):
    service_name: str = "tracking-service"
    called: list[str]

    def build(self) -> None:
        self.called.append("build")

    def deploy(self) -> None:
        self.called.append("deploy")


class TestBdCommand:
    def test_bd_calls_build_then_deploy(self, mock_ctx: Context) -> None:
        space = TrackingServiceSpace(called=[])
        with mock_ctx:
            space.bd()
        assert space.called == ["build", "deploy"]
