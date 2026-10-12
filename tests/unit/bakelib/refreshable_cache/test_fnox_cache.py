import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import typer

from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import FnoxCache
from bakelib.refreshable_cache.fnox import (
    DEFAULT_AGE_KEY_FILE,
    _age_pubkey,
    _ensure_gitignored,
    _fnox_missing_error,
    _project_root,
    run_fnox,
)
from bakelib.space.fnox import FnoxSpace


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
def cache_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    assert FNOX_REAL is not None
    assert AGE_KEYGEN_REAL is not None
    extra = os.pathsep.join({str(Path(FNOX_REAL).parent), str(Path(AGE_KEYGEN_REAL).parent)})
    monkeypatch.setenv("PATH", f"{extra}{os.pathsep}{os.environ['PATH']}")


@pytest.fixture
def cache_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "cache" / "secrets.toml"
    monkeypatch.setattr(FnoxCache, "cache_file", path)
    return path


class TestCacheFileResolution:
    def test_default_is_project_local_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(FnoxCache, "cache_file", None)
        monkeypatch.delenv("BAKE_FNOX_CACHE_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bakefile.py").touch()
        assert _cache()._cache_file() == tmp_path / "fnox.local.toml"

    def test_env_var_used_when_no_class_attr(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(FnoxCache, "cache_file", None)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BAKE_FNOX_CACHE_FILE", str(tmp_path / "env.toml"))
        assert _cache()._cache_file() == tmp_path / "env.toml"

    def test_class_attr_wins_over_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(FnoxCache, "cache_file", tmp_path / "attr.toml")
        monkeypatch.setenv("BAKE_FNOX_CACHE_FILE", str(tmp_path / "env.toml"))
        assert _cache()._cache_file() == tmp_path / "attr.toml"


class TestProjectRoot:
    def test_walks_up_to_marker_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "deep" / "deeper"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        assert _project_root() == tmp_path

    def test_prefers_nearest_fnox_toml(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        (tmp_path / ".git").mkdir()
        inner = tmp_path / "sub"
        inner.mkdir()
        (inner / "fnox.toml").touch()
        monkeypatch.chdir(inner)
        assert _project_root() == inner

    def test_falls_back_to_cwd(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        assert _project_root() == tmp_path


class TestEnsureGitignored:
    def test_creates_gitignore_when_missing(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "fnox.local.toml"
        _ensure_gitignored(cache_file)
        assert (tmp_path / ".gitignore").read_text() == "*.local.toml\n"

    def test_appends_when_not_covered(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("node_modules/\n")
        _ensure_gitignored(tmp_path / "fnox.local.toml")
        assert (tmp_path / ".gitignore").read_text() == "node_modules/\n*.local.toml\n"

    def test_exact_name_counts_as_covered(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("fnox.local.toml\n")
        _ensure_gitignored(tmp_path / "fnox.local.toml")
        assert (tmp_path / ".gitignore").read_text() == "fnox.local.toml\n"


def _make_age_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    key_file = tmp_path / "age.txt"
    subprocess.run(["age-keygen", "-o", str(key_file)], capture_output=True, check=True)
    monkeypatch.setattr(FnoxCache, "age_key_file", key_file)
    return key_file


def _cache() -> FnoxCache[str]:
    return FnoxCache(key="MY_KEY", namespace="ns", fetch_fn=lambda: "unused", cached_type=str)


class TestRunFnoxEnv:
    def test_runs_via_universal_runner_redacted_and_colorless(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # presence-based CLIs in fnox's child chain (bws) color on var
        # presence, so run_fnox relies on color=False (skip injection +
        # remove force vars + NO_COLOR) rather than a hand-rolled env dict
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("CLICOLOR_FORCE", "")
        seen: dict[str, object] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.update(kwargs)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run", fake_run)
        run_fnox(["get", "K"])

        assert seen["color"] is False
        assert seen["redact"] is True
        assert seen["echo"] is False
        assert seen["stream"] is False
        assert seen["check"] is False


class TestArgvShape:
    def test_get_argv(self, monkeypatch: pytest.MonkeyPatch, cache_file: Path) -> None:
        seen: list[list[str]] = []

        def fake_run_fnox(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run_fnox", fake_run_fnox)
        assert _cache()._get_entry() is None
        # cmd excludes the binary, same shape as run_uv ("fnox" added inside)
        assert seen == [["--no-daemon", "-c", str(cache_file), "get", "ns__MY_KEY"]]

    def test_set_argv_has_provider_age(
        self, monkeypatch: pytest.MonkeyPatch, cache_file: Path
    ) -> None:
        # non-empty file skips bootstrap (mocked tests don't spawn real tools)
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text("[providers.age]\n")
        seen: list[list[str]] = []

        def fake_run_fnox(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run_fnox", fake_run_fnox)
        _cache().set("v")
        # value arrives as serialized CacheEntry JSON (timestamp varies)
        cmd = seen[0]
        assert cmd[:5] == [
            "--no-daemon",
            "-c",
            str(cache_file),
            "set",
            "ns__MY_KEY",
        ]
        entry = json.loads(cmd[5])
        assert entry == {"value": "v", "timestamp": entry["timestamp"]}
        # plaintext footgun guard: set NEVER runs without --provider age;
        # provider name must be the distinct bake-cache-age (never a name a
        # committed fnox.toml may also define — providers replace as a unit)
        assert cmd[6:] == ["--provider", "bake-cache-age"]

    def test_delete_argv(self, monkeypatch: pytest.MonkeyPatch, cache_file: Path) -> None:
        seen: list[list[str]] = []

        def fake_run_fnox(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run_fnox", fake_run_fnox)
        _cache().delete()  # nonzero exit tolerated (key may not exist)
        assert seen == [["--no-daemon", "-c", str(cache_file), "remove", "ns__MY_KEY"]]


class TestBootstrap:
    @pytest.mark.usefixtures("cache_on_path")
    def test_writes_provider_block(
        self, monkeypatch: pytest.MonkeyPatch, cache_file: Path, tmp_path: Path
    ) -> None:
        key_file = _make_age_key(monkeypatch, tmp_path)
        pubkey = subprocess.run(
            ["age-keygen", "-y", str(key_file)], capture_output=True, text=True, check=True
        ).stdout.strip()

        _cache().set("v")

        config = cache_file.read_text()
        assert "[providers.bake-cache-age]" in config
        assert 'type = "age"' in config
        assert f'key_file = "{key_file.as_posix()}"' in config
        assert f'"{pubkey}"' in config

    def test_idempotent_keeps_existing_config(
        self, monkeypatch: pytest.MonkeyPatch, cache_file: Path
    ) -> None:
        # bootstrap must not clobber an existing (non-empty) cache file;
        # fnox itself rewrites the toml on set, so assert only our skip logic
        monkeypatch.setattr(
            "bakelib.refreshable_cache.fnox.run_fnox",
            lambda argv: subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
        )
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text('[providers.age]\ntype = "age"\n')

        _cache().set("v")

        assert cache_file.read_text() == '[providers.age]\ntype = "age"\n'

    @pytest.mark.usefixtures("cache_on_path")
    def test_cache_file_gets_0600(
        self, monkeypatch: pytest.MonkeyPatch, cache_file: Path, tmp_path: Path
    ) -> None:
        _make_age_key(monkeypatch, tmp_path)

        _cache().set("v")

        assert (cache_file.stat().st_mode & 0o777) == 0o600

    @pytest.mark.usefixtures("cache_on_path", "cache_file")
    def test_missing_age_key_raises_loud(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # cache_file fixture pins a nonexistent tmp path so bootstrap
        # actually runs (default path could hit a real project file)
        monkeypatch.setattr(FnoxCache, "age_key_file", tmp_path / "nope.txt")
        with pytest.raises(RuntimeError, match="bake setup-fnox"):
            _cache().set("v")


class TestFnoxCheckFailure:
    def test_check_true_raises_on_plain_failure(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        def fake_run_fnox(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Error: no such secret")

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run_fnox", fake_run_fnox)
        with pytest.raises(typer.Exit):
            _cache()._fnox(["get", "ns__MY_KEY"], check=True)
        assert "fnox get failed" in strip_ansi(capsys.readouterr().err)

    def test_check_true_raises_with_auth_hint_on_auth_failure(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        def fake_run_fnox(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="Error: auth_failed: provider rejected the token"
            )

        monkeypatch.setattr("bakelib.refreshable_cache.fnox.run_fnox", fake_run_fnox)
        with pytest.raises(typer.Exit):
            _cache()._fnox(["get", "ns__MY_KEY"], check=True)
        err = strip_ansi(capsys.readouterr().err)
        assert "fnox get failed" in err
        assert "bootstrap credential is missing" in err


class TestAgePubkey:
    def test_missing_age_keygen_binary_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("bakelib.refreshable_cache.fnox.shutil.which", lambda _name: None)
        with pytest.raises(RuntimeError, match="age-keygen not found"):
            _age_pubkey(Path("/tmp/k.txt"))

    def test_age_keygen_failure_raises_with_stderr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bakelib.refreshable_cache.fnox.shutil.which", lambda _name: "/usr/bin/age-keygen"
        )
        monkeypatch.setattr(
            "bakelib.refreshable_cache.fnox.subprocess.run",
            lambda *_a, **_k: subprocess.CompletedProcess([], 1, stdout="", stderr="bad key file"),
        )
        with pytest.raises(RuntimeError, match="bad key file"):
            _age_pubkey(Path("/tmp/k.txt"))


class TestFnoxMissingError:
    def test_mentions_shim_when_fnox_is_mise_shim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bakelib.refreshable_cache.fnox.shutil.which",
            lambda _name: "/home/u/.local/share/mise/shims/fnox",
        )
        assert "shim" in _fnox_missing_error()

    def test_plain_missing_message_without_shim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("bakelib.refreshable_cache.fnox.shutil.which", lambda _name: None)
        assert "fnox not found" in _fnox_missing_error()


class TestCrossModule:
    def test_space_default_is_shared_ssot(self) -> None:
        assert FnoxSpace()._age_key_file() == DEFAULT_AGE_KEY_FILE

    def test_cache_default_is_shared_ssot(self) -> None:
        assert (
            FnoxCache(key="K", fetch_fn=lambda: "x", cached_type=str)._age_key_file()
            == DEFAULT_AGE_KEY_FILE
        )


def _bakebook_cache() -> FnoxCache[str]:
    return FnoxCache(key="MY_KEY", namespace="bakebook", fetch_fn=lambda: "x", cached_type=str)


@pytest.mark.usefixtures("cache_on_path")
def test_real_roundtrip(monkeypatch: pytest.MonkeyPatch, cache_file: Path, tmp_path: Path) -> None:
    _make_age_key(monkeypatch, tmp_path)

    assert _bakebook_cache().get() == "x"  # miss -> fetch_fn (no cache file yet)

    _bakebook_cache().set("cached-value-1")
    config = cache_file.read_text()
    assert "cached-value-1" not in config  # encrypted at rest

    assert _bakebook_cache().get() == "cached-value-1"  # hit via fnox get + age decrypt

    _bakebook_cache().delete()
    assert _bakebook_cache().get() == "x"  # deleted -> miss again


@pytest.mark.usefixtures("cache_on_path")
def test_real_missing_binary_raises(
    monkeypatch: pytest.MonkeyPatch, cache_file: Path, tmp_path: Path
) -> None:
    _make_age_key(monkeypatch, tmp_path)
    # non-empty file skips bootstrap, so the fnox spawn itself is what fails
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text('[providers.age]\ntype = "age"\n')
    monkeypatch.delenv("PATH", raising=False)
    with pytest.raises(RuntimeError, match="fnox not found"):
        _cache().set("v")
