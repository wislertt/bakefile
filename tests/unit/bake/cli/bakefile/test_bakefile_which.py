from pathlib import Path
from typing import Any

import pytest

from bake.cli.bakefile import which as which_mod
from bake.cli.bakefile.which import _print_which, _probe_target_version_string, which
from bake.cli.common.context import context
from bake.cli.common.reinvocation import DetectResult, DetectStatus
from bake.ui.console import ARROW
from bake.ui.logger.capsys import strip_ansi

_TARGET_RAW = "bakefile 0.0.54 from /venv/lib/bake (python 3.12.1)"


def _completed(stdout: str = "", returncode: int = 0) -> Any:
    return type(
        "CompletedProcess", (), {"stdout": stdout, "stderr": "", "returncode": returncode}
    )()


def _fake_run_success(_args: list[str], **_kwargs: Any) -> Any:
    return _completed(_TARGET_RAW)


def _fake_run_fail(*_args: Any, **_kwargs: Any) -> Any:
    return _completed("", returncode=1)


def _detect(status: DetectStatus, python: Path | None = None) -> Any:
    return lambda _p: DetectResult(status, python)


def test_probe_target_version_string_returns_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(which_mod.subprocess, "run", _fake_run_success)
    assert _probe_target_version_string(Path("/venv/python")) == _TARGET_RAW


def test_probe_target_version_string_none_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(which_mod.subprocess, "run", _fake_run_fail)
    assert _probe_target_version_string(Path("/venv/python")) is None


def test_probe_target_version_string_none_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(which_mod.subprocess, "run", lambda *_a, **_k: _completed(""))
    assert _probe_target_version_string(Path("/venv/python")) is None


def test_print_which_no_bakefile(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("no_bakefile"))
    monkeypatch.setattr(which_mod, "_get_version", lambda: "0.0.0")
    _print_which(Path("bakefile.py"))
    out = strip_ansi(capsys.readouterr().out)
    assert "No bakefile.py found here." in out
    assert "would error" in out
    assert "INVOKED Python" in out
    assert "bakefile 0.0.0 from" in out
    assert "Nothing to reinvoke." in out
    assert "Reinvokes under a different Python" not in out


def test_print_which_no_project_python(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("no_project_python"))
    monkeypatch.setattr(which_mod, "_get_version", lambda: "0.0.0")
    _print_which(Path("bakefile.py"))
    out = strip_ansi(capsys.readouterr().out)
    assert "no reinvoked Python could be determined" in out
    assert "would error" in out
    assert "bakefile venv" in out
    assert "bakefile add-inline" in out
    assert "Nothing to reinvoke." in out
    assert "Reinvokes under a different Python" not in out


def test_print_which_unified(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("unified"))
    monkeypatch.setattr(which_mod, "_get_version", lambda: "0.0.0")
    _print_which(Path("bakefile.py"))
    out = strip_ansi(capsys.readouterr().out)
    assert "All commands run on the same Python (invoked == reinvoked):" in out
    assert "bakefile 0.0.0 from" in out
    assert "No reinvoke" in out
    assert ARROW in out
    assert "Reinvokes under a different Python" not in out


def test_print_which_switch_version_differs(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("switch", Path("/venv/python")))
    monkeypatch.setattr(which_mod, "_get_version", lambda: "0.0.63")
    monkeypatch.setattr(which_mod, "_probe_target_version_string", lambda _t: _TARGET_RAW)
    _print_which(Path("bakefile.py"))
    out = strip_ansi(capsys.readouterr().out)
    assert "Reinvokes under a different Python" in out
    assert "bakefile env" in out
    assert "bakefile run" in out
    assert "bakefile lint" in out
    assert "All other bakefile subcommands use INVOKED Python" in out
    assert "Reinvoked Python:  bakefile 0.0.54 from /venv/python" in out
    assert "python 3.12.1" in out
    assert "Invoked Python:" in out
    assert "bakefile 0.0.63" in out
    # Invoked is listed first (chronological: invoke -> reinvoke)
    assert out.index("Invoked Python:") < out.index("Reinvoked Python:")
    assert "5 commands reinvoke to a different Python" in out
    assert "0.0.63 (invoked) → 0.0.54 (reinvoked)" in out
    assert ARROW in out


def test_print_which_switch_same_version(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("switch", Path("/venv/python")))
    monkeypatch.setattr(which_mod, "_get_version", lambda: "0.0.0")
    monkeypatch.setattr(
        which_mod,
        "_probe_target_version_string",
        lambda _t: "bakefile 0.0.0 from /venv/lib/bake (python 3.12.1)",
    )
    _print_which(Path("bakefile.py"))
    out = strip_ansi(capsys.readouterr().out)
    assert "reinvoke to a different Python; bakefile version unchanged" in out
    assert "bakefile version unchanged (0.0.0)" in out


def test_print_which_switch_probe_fails(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("switch", Path("/venv/python")))
    monkeypatch.setattr(which_mod, "_probe_target_version_string", lambda _t: None)
    _print_which(Path("bakefile.py"))
    out = strip_ansi(capsys.readouterr().out)
    assert "(unable to query)" in out
    assert "could not be queried" in out


def test_which_entry_delegates_to_print(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(which_mod, "detect_target_python", _detect("no_bakefile"))
    monkeypatch.setattr(which_mod, "_get_version", lambda: "0.0.0")
    ctx = context()
    which(ctx)
    out = strip_ansi(capsys.readouterr().out)
    assert "No bakefile.py found here." in out
    assert "bakefile 0.0.0 from" in out
