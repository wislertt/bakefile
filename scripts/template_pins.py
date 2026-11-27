import re
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

_PIN = re.compile(
    r"(?P<action>[\w.-]+/[\w./-]+)@(?P<open>\{% editable \w+ %\})?"
    r"(?P<sha>[0-9a-f]{40}) # (?P<tag>[\w.+-]+)"
)


def _pin(match: re.Match[str]) -> str:
    return f"{match['action']}@{match['sha']} # {match['tag']}"


def _restore(match: re.Match[str], new_pins: dict[str, str]) -> str:
    action, rest = new_pins[_pin(match)].split("@", 1)
    return f"{action}@{match['open'] or ''}{rest}"


def _workflow(pins: list[str]) -> str:
    steps = "".join(f"            - uses: {pin}\n" for pin in pins)
    return f"on: push\njobs:\n    bump:\n        runs-on: ubuntu-latest\n        steps:\n{steps}"


def bump_template_pins(paths: Iterable[Path], min_age_days: int) -> list[Path]:
    texts = {path: path.read_text() for path in paths}
    pins = list(dict.fromkeys(_pin(m) for text in texts.values() for m in _PIN.finditer(text)))
    if not pins:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        workflow = Path(tmp) / "pins.yml"
        workflow.write_text(_workflow(pins))
        subprocess.run(
            ["actions-up", "--dir", tmp, "-r", "--yes", "--min-age", str(min_age_days)],
            check=True,
        )
        bumped = [_pin(m) for m in _PIN.finditer(workflow.read_text())]
    if len(bumped) != len(pins):
        raise RuntimeError(
            f"actions-up left {len(bumped)} pins in the workflow, expected {len(pins)}"
        )
    new_pins = dict(zip(pins, bumped, strict=True))
    changed = []
    for path, text in texts.items():
        new_text = _PIN.sub(lambda m: _restore(m, new_pins), text)
        if new_text != text:
            path.write_text(new_text)
            changed.append(path)
    return changed
