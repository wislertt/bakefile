import sys
from pathlib import Path

import pytest

from bake.manage.script_envs import (
    count_script_envs,
    uv_cache_dir,
    warn_if_many_script_envs,
)
from bake.ui import run_uv
from bake.ui.logger import strip_ansi
from bake.utils.constants import CMD_BAKE, CMD_BAKEFILE, DEFAULT_FILE_NAME
from bake.utils.settings import bake_settings
from tests.utils.cli import RunCli

CACHE_ENV_VARS = ("UV_CACHE_DIR", "XDG_CACHE_HOME", "UV_NO_CACHE")


@pytest.fixture(autouse=True)
def _top_level_process(monkeypatch: pytest.MonkeyPatch) -> None:
    # The unit suite marks every process as re-invoked, which skips the check
    monkeypatch.setattr(bake_settings, "bake_reinvoked", False)


def _make_envs(cache_dir: Path, count: int, *, stem: str = "bakefile", bucket: str = "v2") -> None:
    for i in range(count):
        (cache_dir / f"environments-{bucket}" / f"{stem}-{i:016x}").mkdir(parents=True)


def _uv_cache_dir_from_uv(cwd: Path) -> Path:
    result = run_uv(["cache", "dir", "--no-config"], cwd=cwd, echo=False)
    return Path(result.stdout.strip())


class TestUvCacheDirMatchesUv:
    @pytest.fixture(autouse=True)
    def _clear_cache_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in CACHE_ENV_VARS:
            monkeypatch.delenv(name, raising=False)

    def test_default(self, tmp_path: Path) -> None:
        assert uv_cache_dir() == _uv_cache_dir_from_uv(tmp_path)

    def test_uv_cache_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "uv-cache"))
        assert uv_cache_dir() == _uv_cache_dir_from_uv(tmp_path)

    def test_xdg_cache_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
        assert uv_cache_dir() == _uv_cache_dir_from_uv(tmp_path)

    def test_uv_cache_dir_wins_over_xdg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "uv-cache"))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
        assert uv_cache_dir() == _uv_cache_dir_from_uv(tmp_path)

    @pytest.mark.skipif(sys.platform == "win32", reason="XDG applies on Unix only")
    def test_relative_xdg_cache_home_is_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", "relative/xdg")
        assert uv_cache_dir() == _uv_cache_dir_from_uv(tmp_path)


def test_real_script_env_is_found_where_we_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "uv-cache"
    monkeypatch.setenv("UV_CACHE_DIR", str(cache_dir))
    script = tmp_path / DEFAULT_FILE_NAME
    script.write_text("# /// script\n# dependencies = []\n# ///\n")
    run_uv(["sync", "--script", str(script)], cwd=tmp_path, echo=False)
    python = Path(
        run_uv(["python", "find", "--script", str(script)], cwd=tmp_path, echo=False).stdout.strip()
    )

    assert python.parents[3] == cache_dir
    assert uv_cache_dir() == cache_dir
    assert count_script_envs(cache_dir, "bakefile") == 1


class TestUvCacheDirOnWindows:
    @pytest.fixture(autouse=True)
    def _windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in CACHE_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr("bake.manage.script_envs.sys.platform", "win32")

    def test_uses_local_app_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert uv_cache_dir() == tmp_path / "uv" / "cache"

    def test_ignores_xdg_cache_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
        assert uv_cache_dir() == tmp_path / "uv" / "cache"

    def test_none_without_local_app_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        assert uv_cache_dir() is None


class TestCountScriptEnvs:
    def test_counts_only_this_stem(self, tmp_path: Path) -> None:
        _make_envs(tmp_path, 2)
        _make_envs(tmp_path, 5, stem="other")
        (tmp_path / "environments-v2" / "bakefile-file").touch()
        assert count_script_envs(tmp_path, "bakefile") == 2

    def test_counts_every_environments_bucket(self, tmp_path: Path) -> None:
        _make_envs(tmp_path, 2, bucket="v2")
        _make_envs(tmp_path, 3, bucket="v3")
        assert count_script_envs(tmp_path, "bakefile") == 5

    def test_missing_cache_dir_is_zero(self, tmp_path: Path) -> None:
        assert count_script_envs(tmp_path / "gone", "bakefile") == 0


class TestWarnIfManyScriptEnvs:
    @pytest.fixture(autouse=True)
    def _limit_3(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(bake_settings, "bake_script_env_warn_limit", 3)

    def _warn(
        self,
        capfd: pytest.CaptureFixture[str],
        cache_dir: Path,
        file_name: str = DEFAULT_FILE_NAME,
    ) -> str:
        warn_if_many_script_envs(file_name, cache_dir=cache_dir)
        return strip_ansi(capfd.readouterr().err)

    def test_warns_at_limit(self, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
        _make_envs(tmp_path, 3)
        err = self._warn(capfd, tmp_path)
        assert "uv has 3 bakefile-* script environments" in err
        assert "uv cache prune" in err
        assert "BAKE_SCRIPT_ENV_WARN_LIMIT" in err

    def test_quiet_below_limit(self, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
        _make_envs(tmp_path, 2)
        assert self._warn(capfd, tmp_path) == ""

    def test_zero_turns_it_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(bake_settings, "bake_script_env_warn_limit", 0)
        _make_envs(tmp_path, 5)
        assert self._warn(capfd, tmp_path) == ""

    def test_custom_file_name_counts_its_stem(
        self, tmp_path: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        _make_envs(tmp_path, 3, stem="tasks")
        assert "uv has 3 tasks-* script environments" in self._warn(capfd, tmp_path, "tasks.py")

    def test_warns_once_per_process(
        self, tmp_path: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        _make_envs(tmp_path, 3)
        assert self._warn(capfd, tmp_path) != ""
        assert self._warn(capfd, tmp_path) == ""

    def test_quiet_in_reinvoked_child(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(bake_settings, "bake_reinvoked", True)
        _make_envs(tmp_path, 3)
        assert self._warn(capfd, tmp_path) == ""

    def test_defaults_to_uv_cache_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path))
        _make_envs(tmp_path, 3)
        warn_if_many_script_envs(DEFAULT_FILE_NAME)
        assert "uv has 3 bakefile-*" in strip_ansi(capfd.readouterr().err)

    def test_quiet_without_cache_dir(
        self, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("bake.manage.script_envs.uv_cache_dir", lambda: None)
        warn_if_many_script_envs(DEFAULT_FILE_NAME)
        assert strip_ansi(capfd.readouterr().err) == ""

    def test_reads_limit_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BAKE_SCRIPT_ENV_WARN_LIMIT", "250")
        assert type(bake_settings)().bake_script_env_warn_limit == 250


class TestCliWarns:
    @pytest.fixture
    def full_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        cache_dir = tmp_path / "uv-cache"
        _make_envs(cache_dir, 3)
        monkeypatch.setenv("UV_CACHE_DIR", str(cache_dir))
        monkeypatch.setattr(bake_settings, "bake_script_env_warn_limit", 3)
        return cache_dir

    @pytest.fixture
    def work_dir(self, tmp_path: Path) -> Path:
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        return work_dir

    @pytest.mark.parametrize("command", [CMD_BAKE, CMD_BAKEFILE])
    def test_without_bakefile(
        self, full_cache: Path, work_dir: Path, run_cli: RunCli, command: str
    ) -> None:
        _ = full_cache
        result = run_cli(command=command, dir_path=work_dir, args=["--help"])
        assert "uv has 3 bakefile-* script environments" in result.err

    @pytest.mark.parametrize("command", [CMD_BAKE, CMD_BAKEFILE])
    def test_with_project_bakefile(
        self, full_cache: Path, work_dir: Path, run_cli: RunCli, command: str
    ) -> None:
        _ = full_cache
        (work_dir / DEFAULT_FILE_NAME).write_text(
            "from bake import Bakebook\n\nbakebook = Bakebook()\n"
        )
        result = run_cli(command=command, dir_path=work_dir, args=["--help"])
        assert "uv has 3 bakefile-* script environments" in result.err

    def test_quiet_when_turned_off(
        self, full_cache: Path, work_dir: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _ = full_cache
        monkeypatch.setattr(bake_settings, "bake_script_env_warn_limit", 0)
        result = run_cli(command=CMD_BAKE, dir_path=work_dir, args=["--help"])
        assert "script environments" not in result.err
