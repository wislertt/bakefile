import subprocess
from datetime import date

import pytest
import typer

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.dvc import DvcSpace, MediaDvcSpace, _extras_for_url, _gc_args


class DvcSpaceImpl(DvcSpace):
    dvc_remote_name = "origin"
    dvc_remote_url = "s3://test-bucket/path"


class MediaDvcSpaceImpl(MediaDvcSpace):
    dvc_remote_name = "origin"
    dvc_remote_url = "s3://test-bucket/path"


class TestRemoteAttrValidation:
    @pytest.mark.parametrize("space_cls", [DvcSpace, MediaDvcSpace])
    def test_missing_remote_attrs_raise_at_init(self, space_cls: type) -> None:
        with pytest.raises(ValueError, match="dvc_remote_name and dvc_remote_url"):
            space_cls()

    @pytest.mark.parametrize("space_cls", [DvcSpaceImpl, MediaDvcSpaceImpl])
    def test_set_remote_attrs_instantiate(self, space_cls: type) -> None:
        space_cls()


class TestExtrasForUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("s3://bucket/path", ("s3",)),
            ("gs://bucket", ("gs",)),
            ("azure://container", ("azure",)),
            ("ssh://user@host/path", ("ssh",)),
            ("webdav://host", ("webdav",)),
            ("webdavs://host", ("webdav",)),
            ("hdfs://host", ("hadoop",)),
            ("webhdfs://host", ("webhdfs",)),
            ("/local/path", ()),
            ("https://host/path", ()),
            ("unknown://host", ()),
        ],
    )
    def test_scheme_to_extras(self, url: str, expected: tuple[str, ...]) -> None:
        assert _extras_for_url(url) == expected


class TestGcArgs:
    def test_defaults_keep_tips_only(self) -> None:
        today = date(2026, 10, 9)
        assert _gc_args(90, 1, today, cloud=False, dry=False) == [
            "gc",
            "--force",
            "--workspace",
            "--all-branches",
            "--date",
            "2026-07-11",
        ]

    def test_zero_days_omits_date(self) -> None:
        today = date(2026, 10, 9)
        args = _gc_args(0, 1, today, cloud=False, dry=False)
        assert "--date" not in args

    def test_depth_widens_with_num(self) -> None:
        args = _gc_args(90, 3, date(2026, 10, 9), cloud=False, dry=False)
        assert "--num" in args
        assert args[args.index("--num") + 1] == "3"

    def test_dry_and_cloud_flags(self) -> None:
        args = _gc_args(90, 1, date(2026, 10, 9), cloud=True, dry=True)
        assert "--dry" in args
        assert "--cloud" in args


class TestToolSetup:
    def test_mise_tools_include_scheme_extras_for_s3(self) -> None:
        space = DvcSpaceImpl()
        assert "pipx:dvc[extras=s3]" in space._get_mise_tools()

    def test_mise_tools_bare_dvc_for_local_path(self) -> None:
        class LocalSpace(DvcSpaceImpl):
            dvc_remote_url = "/local/path"

        space = LocalSpace()
        assert "pipx:dvc" in space._get_mise_tools()

    def test_mise_tools_include_scheme_extras(self) -> None:
        class WebdavSpace(DvcSpaceImpl):
            dvc_remote_url = "webdavs://host/path"

        space = WebdavSpace()
        assert "pipx:dvc[extras=webdav]" in space._get_mise_tools()

    def test_required_cli_tools_include_dvc(self) -> None:
        space = DvcSpaceImpl()
        assert "dvc" in space._get_required_cli_tools()

    def test_exclude_patterns_protect_dvc_paths(self) -> None:
        space = DvcSpaceImpl()
        patterns = space._get_default_exclude_patterns()
        assert ".dvc" in patterns
        assert "/**/data" in patterns


class TestDvcAdd:
    def test_bare_add_walks_track_globs(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_add()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc add data" in err

    def test_bare_add_skips_dot_dirs(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".venv" / "data").mkdir(parents=True)
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_add()
        captured = capsys.readouterr()
        assert "dvc add" not in strip_ansi(captured.err)

    def test_explicit_path_skips_glob(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_add("custom/dir")
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc add custom/dir" in err

    def test_no_targets_is_noop(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_add()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "Nothing to add" in output


class TestDvcRemoteVerbs:
    def test_push_echoes_push(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_push()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc push" in err

    def test_pull_bare(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_pull()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc pull" in err

    def test_pull_with_path(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_pull("data")
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc pull data" in err

    def test_ping_probes_remote(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_ping()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc ls-url s3://test-bucket/path" in err
        assert "reachable" in err


class TestDvcGc:
    def test_local_gc_runs_real_pipeline_with_dry_flag(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list = []
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        # gc overrides dry-run to execute for real (dvc gc --dry is the
        # native safe rehearsal) — mock ctx.run per non-dry-run pattern
        with mock_ctx:
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            space.dvc_gc()
        assert ["git", "fetch", "--prune"] in calls
        gc_call = next(c for c in calls if c[0] == "dvc")
        assert gc_call == [
            "dvc",
            "gc",
            "--force",
            "--workspace",
            "--all-branches",
            "--date",
            gc_call[gc_call.index("--date") + 1],
            "--dry",
        ]
        assert "--cloud" not in gc_call

    def test_cloud_gc_mirrors_origin_branches(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list = []
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            calls.append(cmd)
            stdout = ""
            if "for-each-ref" in cmd and "refs/remotes/origin" in cmd:
                stdout = "refs/remotes/origin/main\nrefs/remotes/origin/HEAD\n"
            elif "for-each-ref" in cmd:
                stdout = ""
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")

        with mock_ctx, mock_ctx.override_dry_run(False):
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            space.dvc_gc(cloud=True)
        branch_call = ["git", "branch", "main", "refs/remotes/origin/main"]
        assert branch_call in calls
        gc_call = next(c for c in calls if c[:2] == ["dvc", "gc"])
        assert "--cloud" in gc_call

    def test_cloud_gc_hard_fails_on_fetch_failure(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")

        with mock_ctx, mock_ctx.override_dry_run(False):
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            with pytest.raises(typer.Exit):
                space.dvc_gc(cloud=True)
        assert "git fetch failed" in strip_ansi(capsys.readouterr().err)


class TestDvcCheck:
    def test_no_dvc_repo_is_noop(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_check()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "No dvc repo" in output

    def test_clean_state_reports_clean(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dvc").mkdir()
        space = DvcSpaceImpl()
        with mock_ctx:
            space.dvc_check()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc state clean" in err

    def test_missing_remote_url_is_problem(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dvc").mkdir()

        space = DvcSpaceImpl()
        monkeypatch.setattr(type(space), "dvc_remote_url", "")
        with mock_ctx, pytest.raises(typer.Exit):
            space.dvc_check()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "no remote url" in output
        assert "1 problem(s)" in output

    def test_untracked_data_is_problem(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dvc").mkdir()
        (tmp_path / "data").mkdir()
        space = DvcSpaceImpl()
        with mock_ctx, pytest.raises(typer.Exit):
            space.dvc_check()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "untracked data" in output
        assert "bake dvc add" in output

    def test_full_problem_report(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dvc").mkdir()
        (tmp_path / "data").mkdir()  # no data.dvc -> untracked data
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            stdout = ""
            if cmd[:3] == ["dvc", "data", "status"] and "--not-in-remote" not in cmd:
                stdout = (
                    '{"not_in_cache": ["data/gone"],'
                    ' "uncommitted": {"deleted": ["data/gone"],'
                    ' "modified": ["data/drift", "data/gone"]}}'
                )
            elif cmd[:3] == ["dvc", "data", "status"]:
                return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")
            elif cmd[0] == "git" and "status" in cmd:
                stdout = "?? new.dvc\n M dirty.dvc\n"
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")

        with mock_ctx:
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            with pytest.raises(typer.Exit):
                space.dvc_check()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        # data/drift: uncommitted-modified, backed by cache -> drift problem
        # data/gone: not_in_cache -> un-materialized warning, not drift
        assert "4 problem(s)" in output
        assert "1 warning(s)" in output
        assert "drift" in output
        assert "untracked meta" in output
        assert "unstaged meta" in output
        assert "remote check failed" in output
        assert "required:" in output
        assert "git add '*.dvc'" in output
        assert "bake dvc pull" in output  # un-materialized warning -> optional
        assert "unstaged meta = pushed-but-uncommitted gap" in output

    def test_warning_only_report_exits_zero(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dvc").mkdir()
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            stdout = ""
            if cmd[:3] == ["dvc", "data", "status"] and "--not-in-remote" not in cmd:
                stdout = '{"not_in_cache": ["data/gone"], "uncommitted": {}}'
            elif cmd[:3] == ["dvc", "data", "status"]:
                stdout = '{"not_in_remote": ["data/gone"]}'
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")

        with mock_ctx:
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            space.dvc_check()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "problem(s)" not in output
        assert "2 warning(s)" in output
        assert "un-materialized" in output
        assert "un-pushed" in output
        assert "optional:" in output
        assert "bake dvc pull" in output
        assert "bake dvc push" in output


class TestDvcEnv:
    class SecretSpace(DvcSpaceImpl):
        dvc_secret_keys = ("AWS_ACCESS_KEY_ID",)

    def test_dvc_env_injects_present_secrets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        space = self.SecretSpace()
        monkeypatch.setattr(type(space), "get_secret", lambda _self, _key: "s3cr3t")
        env = space._dvc_env()
        assert env["AWS_ACCESS_KEY_ID"] == "s3cr3t"

    def test_dvc_env_exits_on_missing_secret(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        space = self.SecretSpace()
        monkeypatch.setattr(type(space), "get_secret", lambda _self, _key: None)
        with pytest.raises(typer.Exit):
            space._dvc_env()
        err = strip_ansi(capsys.readouterr().err)
        assert "Missing DVC remote credentials" in err
        assert "bake secret set AWS_ACCESS_KEY_ID" in err

    def test_remote_env_none_on_missing_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        space = self.SecretSpace()
        monkeypatch.setattr(type(space), "get_secret", lambda _self, _key: None)
        assert space._remote_env() is None

    def test_remote_env_injects_present_secrets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        space = self.SecretSpace()
        monkeypatch.setattr(type(space), "get_secret", lambda _self, _key: "s3cr3t")
        env = space._remote_env()
        assert env is not None
        assert env["AWS_ACCESS_KEY_ID"] == "s3cr3t"

    def test_check_skips_remote_pass_without_creds(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dvc").mkdir()
        space = self.SecretSpace()
        monkeypatch.setattr(type(space), "get_secret", lambda _self, _key: None)
        with mock_ctx:
            space.dvc_check()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "remote check skipped: missing creds" in output
        assert "dvc state clean" in output

    def test_cloud_gc_passes_creds_env(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list = []
        space = self.SecretSpace()
        monkeypatch.setattr(type(space), "get_secret", lambda _self, _key: "s3cr3t")

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            stdout = ""
            if "for-each-ref" in cmd and "refs/remotes/origin" in cmd:
                stdout = "refs/remotes/origin/main\n"
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")

        with mock_ctx, mock_ctx.override_dry_run(False):
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            space.dvc_gc(cloud=True)
        gc_env = next(kw["env"] for cmd, kw in calls if cmd[:2] == ["dvc", "gc"])
        assert gc_env["AWS_ACCESS_KEY_ID"] == "s3cr3t"


class TestEnsureDvcRemote:
    def test_empty_url_errors(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        space = DvcSpaceImpl()
        monkeypatch.setattr(type(space), "dvc_remote_url", "")
        with mock_ctx, pytest.raises(typer.Exit):
            space._ensure_dvc_remote()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc_remote_url is empty" in err

    def test_initializes_repo_and_remote(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space._ensure_dvc_remote()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc init" in err
        assert "dvc remote add origin s3://test-bucket/path" in err
        assert "dvc config core.remote origin" in err
        assert "dvc remote 'origin' -> s3://test-bucket/path" in err

    def test_idempotent_when_config_matches(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        dvc_dir = tmp_path / ".dvc"
        dvc_dir.mkdir()
        (dvc_dir / "config").write_text(
            '[core]\n    remote = origin\n[remote "origin"]\n    url = s3://test-bucket/path\n'
        )
        space = DvcSpaceImpl()
        with mock_ctx:
            space._ensure_dvc_remote()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc init" not in err
        assert "remote add" not in err
        assert "remote modify" not in err
        assert "dvc config" not in err
        assert "dvc remote 'origin' -> s3://test-bucket/path" in err

    def test_updates_changed_url(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        dvc_dir = tmp_path / ".dvc"
        dvc_dir.mkdir()
        (dvc_dir / "config").write_text(
            '[core]\n    remote = origin\n[remote "origin"]\n    url = s3://old/path\n'
        )
        space = DvcSpaceImpl()
        with mock_ctx:
            space._ensure_dvc_remote()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc remote modify origin url s3://test-bucket/path" in err


class TestAssertDvcRemoteFailure:
    def test_unreachable_remote_hard_fails(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")

        with mock_ctx:
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            with pytest.raises(typer.Exit):
                space._assert_dvc_remote()
        err = strip_ansi(capsys.readouterr().err)
        assert "unreachable" in err
        assert "s3://test-bucket/path" in err


class TestLifecycleHooks:
    def test_setup_project_ensures_remote_and_pre_push_hook(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space._setup_project()
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc init" in err
        assert "remote add origin" in err
        assert "pre-commit install --hook-type pre-push" in err

    def test_lint_runs_dvc_check(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space.lint()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out + captured.err)
        assert "No dvc repo" in output

    def test_assert_setup_dev_probes_remote(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = DvcSpaceImpl()
        with mock_ctx:
            space.assert_setup_dev(fast=1)
        err = strip_ansi(capsys.readouterr().err)
        assert "dvc ls-url s3://test-bucket/path" in err
        assert "reachable" in err


class TestFetchDegradation:
    def test_local_gc_warns_on_fetch_failure(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        space = DvcSpaceImpl()

        def fake_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")

        with mock_ctx:
            monkeypatch.setattr(mock_ctx, "run", fake_run)
            space.dvc_gc()
        err = strip_ansi(capsys.readouterr().err)
        assert "git fetch failed — keeping local branches only" in err
