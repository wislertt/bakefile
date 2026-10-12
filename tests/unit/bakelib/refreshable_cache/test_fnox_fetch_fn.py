import dataclasses
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import typer

from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import FnoxFetchFn


def _real_bin(name: str) -> str | None:
    found = shutil.which(name)
    if found is None:
        return None
    # mise shims fail outside a mise-configured dir; `mise which` resolves
    # the real binary so the tests work from a tmp cwd
    if "shims" not in Path(found).parts:
        return found
    result = subprocess.run(["mise", "which", name], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


FNOX_REAL = _real_bin("fnox")
AGE_KEYGEN_REAL = _real_bin("age-keygen")


@pytest.fixture
def tools_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    assert FNOX_REAL is not None
    assert AGE_KEYGEN_REAL is not None
    extra = os.pathsep.join({str(Path(FNOX_REAL).parent), str(Path(AGE_KEYGEN_REAL).parent)})
    monkeypatch.setenv("PATH", f"{extra}{os.pathsep}{os.environ['PATH']}")


def _setup_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    key_file = tmp_path / "age.txt"
    subprocess.run(["age-keygen", "-o", str(key_file)], capture_output=True, check=True)
    pubkey = subprocess.run(
        ["age-keygen", "-y", str(key_file)], capture_output=True, text=True, check=True
    ).stdout.strip()
    (tmp_path / "fnox.toml").write_text(
        f'[providers.age]\ntype = "age"\nkey_file = "{key_file}"\nrecipients = ["{pubkey}"]\n'
    )


class TestArgvShape:
    def test_base_argv(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[list[str]] = []

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="v\n", stderr="")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run", fake_run)
        FnoxFetchFn(key="MY_KEY")()
        assert seen == [["fnox", "--no-daemon", "get", "MY_KEY"]]

    def test_profile_flag_passed_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[list[str]] = []

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="v\n", stderr="")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run", fake_run)
        FnoxFetchFn(key="MY_KEY", profile="dev")()
        assert seen == [["fnox", "--no-daemon", "--profile", "dev", "get", "MY_KEY"]]


class TestContract:
    def test_is_frozen_dataclass(self) -> None:
        fetch = FnoxFetchFn(key="MY_KEY")
        with pytest.raises(dataclasses.FrozenInstanceError):
            fetch.key = "OTHER"  # ty: ignore[invalid-assignment]

    def test_carries_key_for_cache_registration(self) -> None:
        assert FnoxFetchFn(key="MY_KEY").key == "MY_KEY"


@pytest.mark.usefixtures("tools_on_path")
def test_real_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup_project(monkeypatch, tmp_path)

    # BEFORE set: provider block only, no secret entry, key on disk
    config_before = (tmp_path / "fnox.toml").read_text()
    key_before = (tmp_path / "age.txt").read_text()
    assert "MY_KEY" not in config_before
    assert "AGE-SECRET-KEY-1" in key_before

    subprocess.run(
        ["fnox", "--no-daemon", "set", "MY_KEY", "try-value-123", "--provider", "age"],
        capture_output=True,
        text=True,
        check=True,
    )

    # AFTER set: fnox rewrote fnox.toml with an age-encrypted entry.
    # plaintext absent = encryption actually happened
    config_after = (tmp_path / "fnox.toml").read_text()
    assert "MY_KEY" in config_after
    assert 'provider = "age"' in config_after
    assert "try-value-123" not in config_after
    assert (tmp_path / "age.txt").read_text() == key_before

    assert FnoxFetchFn(key="MY_KEY")() == "try-value-123"

    # AFTER fetch: files unchanged, plaintext only in memory/stdout
    assert (tmp_path / "fnox.toml").read_text() == config_after
    assert (tmp_path / "age.txt").read_text() == key_before


@pytest.mark.usefixtures("tools_on_path")
def test_real_missing_key_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    _setup_project(monkeypatch, tmp_path)
    with pytest.raises(typer.Exit):
        FnoxFetchFn(key="MY_KEY")()
    err = strip_ansi(capsys.readouterr().err)
    assert "fnox get MY_KEY failed" in err
    assert "bootstrap credential is missing" not in err  # plain miss is not an auth failure


def test_missing_binary_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PATH", raising=False)
    with pytest.raises(RuntimeError, match="fnox not found"):
        FnoxFetchFn(key="MY_KEY")()


class TestBootstrapFetchFn:
    def test_missing_store_exits_with_hint(self, capsys: pytest.CaptureFixture) -> None:
        from bakelib.refreshable_cache.fnox import BootstrapFetchFn

        with pytest.raises(typer.Exit):
            BootstrapFetchFn(key="FNOX_X_TOKEN", label="Tok")()
        err = capsys.readouterr().err
        assert "FNOX_X_TOKEN is not stored" in err
        assert "bake setup-fnox" in err


class TestAuthFailedHint:
    def test_returns_hint_when_auth_failed_marker_present(self) -> None:
        from bakelib.refreshable_cache.fnox import _auth_failed_hint

        hint = _auth_failed_hint("Error: auth_failed: provider rejected token")
        assert hint is not None
        assert "bake setup-fnox" in hint
        assert "env wins over the store" in hint

    def test_returns_none_for_other_errors(self) -> None:
        from bakelib.refreshable_cache.fnox import _auth_failed_hint

        assert _auth_failed_hint("Error: decryption failed") is None


class TestFetchFailureOutput:
    def test_failure_prints_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Error: no such secret")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run", fake_run)
        with pytest.raises(typer.Exit):
            FnoxFetchFn(key="MY_KEY")()

    def test_auth_failure_prints_bootstrap_hint(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                argv, 1, stdout="", stderr="Error: auth_failed: provider rejected the token"
            )

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run", fake_run)
        with pytest.raises(typer.Exit):
            FnoxFetchFn(key="MY_KEY")()
        err = strip_ansi(capsys.readouterr().err)
        assert "fnox get MY_KEY failed" in err
        assert "bootstrap credential is missing" in err
        assert "env wins over the store" in err
