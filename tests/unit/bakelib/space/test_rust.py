from pathlib import Path
from unittest import mock

import pytest

from bake import Context
from bakelib.space.base import BaseSpace
from bakelib.space.rust import RustSpace

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

    def test_get_tools_includes_rustup_and_cargo(self) -> None:
        space = RustSpace()
        tools = space._get_tools()
        assert "rustup" in tools
        assert "cargo" in tools

    def test_package_name_returns_cargo_package_name(self, tmp_path: Path) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)

        space = RustSpace()
        with mock.patch("bakelib.space.rust.Path", return_value=cargo_toml):
            assert space.package_name() == "test-package"

    def test_current_version_returns_cargo_version(self, tmp_path: Path) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)

        space = RustSpace()
        with mock.patch("bakelib.space.rust.Path", return_value=cargo_toml):
            assert space.current_version() == "1.2.3"

    def test_set_version_updates_cargo_toml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)

        space = RustSpace()
        monkeypatch.chdir(tmp_path)

        space._set_version("2.0.0")

        result = cargo_toml.read_text()
        assert 'version = "2.0.0"' in result
