import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar, get_origin

import pytest

from bake import Context
from bake.cli.common.context import context
from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import (
    FnoxCache,
    MemoryCache,
    SecretUtilsFnoxCacheRegistry,
    SecretUtilsKeyringCacheRegistry,
)
from bakelib.space.base import BaseSpace
from bakelib.space.fnox import FnoxSpace
from bakelib.utils.secret import SecretUtils


def test_vault_uses_fnox_backends() -> None:
    vault = FnoxSpace().vault()
    assert isinstance(vault, SecretUtilsFnoxCacheRegistry)
    assert vault.backends == [MemoryCache, FnoxCache]
    assert vault.namespace == "bakebook"


def test_base_secret_utils_keeps_keyring() -> None:
    assert get_origin(SecretUtils._cache_registry_cls) is SecretUtilsKeyringCacheRegistry


def test_fnox_space_is_base_space() -> None:
    assert issubclass(FnoxSpace, BaseSpace)


def test_mise_tools_include_age_and_fnox() -> None:
    tools = FnoxSpace()._get_mise_tools()
    assert "age" in tools
    assert "fnox" in tools


def test_required_cli_tools_include_age_and_fnox() -> None:
    tools = FnoxSpace()._get_required_cli_tools()
    assert tools["age"] is None
    assert tools["fnox"] is None


def test_fnox_age_key_file_field_overrides_everything(tmp_path: Path) -> None:
    key_file = tmp_path / "custom" / "key.txt"
    space = FnoxSpace(fnox_age_key_file=key_file)
    assert space._age_key_file() == key_file


def test_fnox_age_key_file_defaults_to_fnox_config_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FNOX_AGE_KEY_FILE", raising=False)
    assert FnoxSpace()._age_key_file() == Path.home() / ".config" / "fnox" / "age.txt"


class TestEnsureAgeKey:
    def test_skips_keygen_when_key_exists(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "age.txt"
        key_file.write_text("AGE-SECRET-KEY-1...")
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space._ensure_age_key()
        err = strip_ansi(capsys.readouterr().err)
        assert "age-keygen" not in err
        assert str(key_file) in err

    def test_keygen_runs_when_key_missing(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "cfg" / "age.txt"
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space._ensure_age_key()
        err = strip_ansi(capsys.readouterr().err)
        assert "age-keygen" in err
        assert str(key_file) in err
        assert f"age key: {key_file}" in err

    def test_dry_run_does_not_create_key_dir(self, mock_ctx: Context, tmp_path: Path) -> None:
        key_file = tmp_path / "cfg" / "age.txt"
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space._ensure_age_key()
        assert not key_file.parent.exists()


class TestAssertAgeKey:
    def test_success_when_key_exists(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "age.txt"
        key_file.write_text("AGE-SECRET-KEY-1...")
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space._assert_age_key()
        err = strip_ansi(capsys.readouterr().err)
        assert str(key_file) in err
        assert "not found" not in err

    def test_error_when_key_missing(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "missing.txt"
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space._assert_age_key()
        err = strip_ansi(capsys.readouterr().err)
        assert "not found" in err
        assert "bake setup-fnox" in err


class TestSetupProjectHook:
    def test_setup_project_ensures_age_key(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        key_file = tmp_path / "cfg" / "age.txt"
        monkeypatch.chdir(tmp_path)
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space._setup_project()
        err = strip_ansi(capsys.readouterr().err)
        assert "age-keygen" in err


class TestSetupFnoxCommand:
    def test_runs_age_step_and_skips_bootstrap_when_empty(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        key_file = tmp_path / "age.txt"
        key_file.write_text("AGE-SECRET-KEY-1...")
        space = FnoxSpace(fnox_age_key_file=key_file)
        with mock_ctx:
            space.setup_fnox()
        err = strip_ansi(capsys.readouterr().err)
        assert f"age key: {key_file}" in err


class TestEnsureAgeKeyRealRun:
    def test_creates_key_and_parent_dir_when_not_dry_run(self, tmp_path: Path) -> None:
        _require_real_bins()
        key_file = tmp_path / "cfg" / "age.txt"
        with context(chdir=tmp_path, dry_run=False):
            FnoxSpace(fnox_age_key_file=key_file)._ensure_age_key()
        assert key_file.exists()


class TestAssertSetupDev:
    def test_asserts_age_key_and_bootstrap_secrets(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        _seed_store()

        class Demo(FnoxSpace[str | None]):
            fnox_bootstrap_secrets: ClassVar[Mapping[str, str]] = {"FNOX_X_TOKEN": "Tok"}

            def lint(self) -> None:
                raise AssertionError("fast=2 must skip lint")

            def test(self) -> None:
                raise AssertionError("fast=2 must skip test")

        space = Demo(fnox_age_key_file=tmp_path / "age.txt")
        try:
            with mock_ctx:
                space.assert_setup_dev(fast=2)
        finally:
            os.environ.pop("FNOX_X_TOKEN", None)
        err = strip_ansi(capsys.readouterr().err)
        assert f"age key: {tmp_path / 'age.txt'}" in err
        assert "fnox get FNOX_X_TOKEN" in err
        assert "FNOX_X_TOKEN: cached" in err


def _require_real_bins() -> None:
    assert shutil.which("fnox") is not None, "fnox binary required"
    assert shutil.which("age-keygen") is not None, "age-keygen binary required"


def _patch_fnox_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # point FnoxCache class overrides at a disposable age key + store
    monkeypatch.chdir(tmp_path)
    key_file = tmp_path / "age.txt"
    subprocess.run(["age-keygen", "-o", str(key_file)], capture_output=True, check=True)
    monkeypatch.setattr(FnoxCache, "age_key_file", key_file)
    monkeypatch.setattr(FnoxCache, "cache_file", tmp_path / "fnox.local.toml")


def _seed_store(value: str = "tok-value-123") -> None:
    cache = FnoxCache(
        key="FNOX_X_TOKEN", namespace="bakebook", fetch_fn=lambda: "", cached_type=str
    )
    cache.set(value)


def _demo_space() -> FnoxSpace[str | None]:
    class Demo(FnoxSpace[str | None]):
        fnox_bootstrap_secrets: ClassVar[Mapping[str, str]] = {"FNOX_X_TOKEN": "Tok"}

    return Demo()


class TestEnsureBootstrapSecretsBranches:
    def test_cached_value_skips_prompt(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        _seed_store()

        def _no_prompt(*_a: object, **_k: object) -> str:
            raise AssertionError("must not prompt when value is cached")

        monkeypatch.setattr("bakelib.space.fnox.typer.confirm", _no_prompt)
        try:
            with context(chdir=tmp_path, dry_run=False):
                _demo_space()._ensure_bootstrap_secrets()
        finally:
            os.environ.pop("FNOX_X_TOKEN", None)
        assert "FNOX_X_TOKEN: cached" in strip_ansi(capsys.readouterr().err)

    def test_dry_run_reports_prompt_without_asking(
        self,
        capsys: pytest.CaptureFixture,
        mock_ctx: Context,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        with mock_ctx:
            _demo_space()._ensure_bootstrap_secrets()
        err = strip_ansi(capsys.readouterr().err)
        assert "Would prompt for FNOX_X_TOKEN" in err

    def test_declined_confirm_skips_secret(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        monkeypatch.setattr("bakelib.space.fnox.typer.confirm", lambda *_a, **_k: False)
        space = _demo_space()
        with context(chdir=tmp_path, dry_run=False):
            space._ensure_bootstrap_secrets()
        err = strip_ansi(capsys.readouterr().err)
        assert "Skipped FNOX_X_TOKEN" in err
        assert "will fail auth until it is set" in err


class TestAssertBootstrapSecrets:
    def test_noop_when_no_bootstrap_secrets(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        with mock_ctx:
            FnoxSpace()._assert_bootstrap_secrets()
        assert "not stored" not in strip_ansi(capsys.readouterr().err)

    def test_success_when_cached(
        self,
        capsys: pytest.CaptureFixture,
        mock_ctx: Context,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        _seed_store()
        try:
            with mock_ctx:
                _demo_space()._assert_bootstrap_secrets()
        finally:
            os.environ.pop("FNOX_X_TOKEN", None)
        err = strip_ansi(capsys.readouterr().err)
        assert "fnox get FNOX_X_TOKEN" in err
        assert "FNOX_X_TOKEN: cached" in err

    def test_error_when_not_stored(
        self,
        capsys: pytest.CaptureFixture,
        mock_ctx: Context,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        with mock_ctx:
            _demo_space()._assert_bootstrap_secrets()
        err = strip_ansi(capsys.readouterr().err)
        assert "FNOX_X_TOKEN not stored" in err
        assert "bake setup-fnox" in err


class TestBootstrapSecrets:
    def test_vault_registers_bootstrap_as_tracked_key(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        _seed_store()
        try:
            vault = _demo_space().vault()
            assert "FNOX_X_TOKEN" in vault
            assert ("FNOX_X_TOKEN", True) in vault.list_entries()
        finally:
            os.environ.pop("FNOX_X_TOKEN", None)

    def test_vault_exports_bootstrap_to_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        _seed_store()
        monkeypatch.delenv("FNOX_X_TOKEN", raising=False)
        try:
            _demo_space().vault()
            assert os.environ["FNOX_X_TOKEN"] == "tok-value-123"
        finally:
            os.environ.pop("FNOX_X_TOKEN", None)

    def test_env_wins_over_store(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        _seed_store()
        monkeypatch.setenv("FNOX_X_TOKEN", "from-env")
        try:
            _demo_space().vault()
            assert os.environ["FNOX_X_TOKEN"] == "from-env"
        finally:
            os.environ.pop("FNOX_X_TOKEN", None)

    def test_missing_store_registers_key_without_export(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _require_real_bins()
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("FNOX_X_TOKEN", raising=False)
        vault = _demo_space().vault()
        assert "FNOX_X_TOKEN" in vault
        assert ("FNOX_X_TOKEN", False) in vault.list_entries()
        assert "FNOX_X_TOKEN" not in os.environ

    def test_ensure_prompts_and_stores_on_miss(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _require_real_bins()
        _patch_fnox_store(monkeypatch, tmp_path)
        monkeypatch.setattr("bakelib.space.fnox.typer.confirm", lambda *_a, **_k: True)
        monkeypatch.setattr("bakelib.space.fnox.typer.prompt", lambda *_a, **_k: "pasted-value")
        space = _demo_space()
        with context(chdir=tmp_path, dry_run=False):
            space._ensure_bootstrap_secrets()
        assert space.vault().has_value("FNOX_X_TOKEN")
        err = strip_ansi(capsys.readouterr().err)
        assert "FNOX_X_TOKEN: cached" in err
