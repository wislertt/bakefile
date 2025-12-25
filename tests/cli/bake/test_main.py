import sys
from pathlib import Path

import pytest

from bakefile.cli.bake.main import main


class TestMain:
    def test_main_help(
        self,
        examples_simple_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["bake", "--help", "-C", str(examples_simple_dir)])
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "--chdir" in captured.out and "-C" in captured.out
        assert "--file-name" in captured.out and "-f" in captured.out
        assert "--book-name" in captured.out and "-b" in captured.out

    def test_main_help2(
        self,
        examples_no_bakebook_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["bake", "--help", "-C", str(examples_no_bakebook_dir)])
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "--chdir" in captured.out and "-C" in captured.out
        assert "--file-name" in captured.out and "-f" in captured.out
        assert "--book-name" in captured.out and "-b" in captured.out
