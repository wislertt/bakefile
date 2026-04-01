import pytest
import typer
from pydantic import ValidationError

from bake import Context
from bakelib.environ.base import BaseEnv
from bakelib.space.service import BaseServiceSpace


class ConcreteServiceSpace(BaseServiceSpace[BaseEnv]):
    env: BaseEnv = BaseEnv("dev")
    service_name: str = "test-service"


class TestBareServiceSpace:
    def test_init_raises_without_service_name(self) -> None:
        with pytest.raises(ValidationError):
            BaseServiceSpace()  # ty: ignore[missing-argument]

    def test_init_raises_without_env(self) -> None:
        with pytest.raises(ValidationError):
            BaseServiceSpace(service_name="my-service")  # ty: ignore[missing-argument]


class TestServiceSpaceInit:
    def test_init_with_service_name_and_env(self) -> None:
        space = ConcreteServiceSpace()
        assert space.service_name == "test-service"
        assert str(space.env) == "dev"


class TestBuildCommand:
    def test_build_command_exits_with_code_1(self, mock_ctx: Context) -> None:
        space = ConcreteServiceSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                space.build()
            assert exc_info.value.exit_code == 1


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
