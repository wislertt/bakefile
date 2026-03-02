import subprocess
from pathlib import Path
from unittest import mock

import pytest

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.base import BaseSpace
from bakelib.space.rust import RustSpace, run_rustup_update

_CARGO_TOML_CONTENT = """\
[package]
name = "test-package"
version = "1.2.3"
"""


def test_rust_space_is_base_space() -> None:
    assert issubclass(RustSpace, BaseSpace)


class TestRustSpace:
    def test_lint_runs_all_commands(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        space = RustSpace()
        with mock_ctx:
            space.lint()
        captured = capsys.readouterr()
        assert "cargo +nightly check --tests" in captured.err
        assert "cargo +nightly fmt" in captured.err
        assert "cargo +nightly clippy" in captured.err

    def test_update_runs_rustup_and_cargo_update(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = RustSpace()
        with mock_ctx:
            space.update()
        captured = capsys.readouterr()
        assert "rustup update" in captured.err
        assert "cargo update" in captured.err

    def test_get_required_cli_tools_includes_rustup_and_cargo(self) -> None:
        space = RustSpace()
        tools = space._get_required_cli_tools()
        assert "rustup" in tools
        assert "cargo" in tools

    def test_package_name_returns_cargo_package_name(self, tmp_path: Path) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)

        space = RustSpace()
        with mock.patch("bakelib.space.rust.Path", return_value=cargo_toml):
            assert space._package_name == "test-package"

    def test_version_returns_cargo_version(self, tmp_path: Path) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)

        space = RustSpace()
        with mock.patch("bakelib.space.rust.Path", return_value=cargo_toml):
            assert space._version == "1.2.3"

    def test_set_version_updates_cargo_toml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_ctx: Context
    ) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)

        space = RustSpace()
        monkeypatch.chdir(tmp_path)

        with mock_ctx:
            mock_ctx.obj.dry_run = False
            space._set_version_in_cargo_toml("2.0.0")

        result = cargo_toml.read_text()
        assert 'version = "2.0.0"' in result

    def test_setup_tools_runs_rustup_update(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = RustSpace()
        with mock_ctx:
            space.setup_tools()
        captured = capsys.readouterr()
        assert "rustup update" in captured.err


class TestRunRustupUpdate:
    def test_timeout_logs_warning(self, capsys: pytest.CaptureFixture) -> None:
        def mock_run_timeout(*_, **__):
            raise subprocess.TimeoutExpired(cmd="rustup update", timeout=30)

        run_rustup_update(mock_run_timeout, timeout=0.1, max_attempts=1)

        captured = capsys.readouterr()
        assert "`rustup update` timed out after 1 attempts" in strip_ansi(captured.err)
