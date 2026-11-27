import re
import subprocess
from pathlib import Path

import pytest

from scripts.template_pins import bump_template_pins

OLD_SHA = "a" * 40
NEW_SHA = "b" * 40
OTHER_SHA = "c" * 40


class FakeActionsUp:
    def __init__(self, bumps: dict[str, str]):
        self.bumps = bumps
        self.calls: list[list[str]] = []
        self.workflows: list[str] = []

    def __call__(self, args: list[str], **_kwargs) -> subprocess.CompletedProcess:
        self.calls.append(args)
        directory = Path(args[args.index("--dir") + 1])
        for workflow in directory.rglob("*.yml"):
            text = workflow.read_text()
            self.workflows.append(text)
            for old, new in self.bumps.items():
                text = text.replace(old, new)
            workflow.write_text(text)
        return subprocess.CompletedProcess(args, 0)


@pytest.fixture
def actions_up(monkeypatch):
    fake = FakeActionsUp(
        {f"actions/checkout@{OLD_SHA} # v1.0.0": f"actions/checkout@{NEW_SHA} # v1.1.0"}
    )
    monkeypatch.setattr("scripts.template_pins.subprocess.run", fake)
    return fake


@pytest.mark.usefixtures("actions_up")
def test_bumps_pin_in_yml_template(tmp_path):
    template = tmp_path / "ci.yml"
    template.write_text(
        "jobs:\n"
        "    check:\n"
        "        # (editable) steps\n"
        "{% editable steps %}\n"
        "        steps:\n"
        f"            - uses: actions/checkout@{OLD_SHA} # v1.0.0\n"
        "{% endeditable %}\n"
    )

    changed = bump_template_pins([template], min_age_days=3)

    assert changed == [template]
    assert template.read_text() == (
        "jobs:\n"
        "    check:\n"
        "        # (editable) steps\n"
        "{% editable steps %}\n"
        "        steps:\n"
        f"            - uses: actions/checkout@{NEW_SHA} # v1.1.0\n"
        "{% endeditable %}\n"
    )


@pytest.mark.usefixtures("actions_up")
def test_bumps_pin_in_python_string_and_keeps_other_text(tmp_path):
    module = tmp_path / "inserts.py"
    module.write_text(
        'CHILD_JOB = """\\\n'
        "audit:\n"
        "    steps:\n"
        f"        - uses: actions/checkout@{OLD_SHA} # v1.0.0\n"
        f"        - uses: other/action@{OTHER_SHA} # v2.0.0\n"
        '"""\n'
    )

    bump_template_pins([module], min_age_days=3)

    assert module.read_text() == (
        'CHILD_JOB = """\\\n'
        "audit:\n"
        "    steps:\n"
        f"        - uses: actions/checkout@{NEW_SHA} # v1.1.0\n"
        f"        - uses: other/action@{OTHER_SHA} # v2.0.0\n"
        '"""\n'
    )


def test_keeps_inline_editable_tags_around_pin(tmp_path, actions_up):
    template = tmp_path / "security.yml"
    template.write_text(
        "              uses: actions/checkout@{% editable checkout_pin %}"
        f"{OLD_SHA} # v1.0.0{{% endeditable %}}\n"
    )

    bump_template_pins([template], min_age_days=3)

    assert template.read_text() == (
        "              uses: actions/checkout@{% editable checkout_pin %}"
        f"{NEW_SHA} # v1.1.0{{% endeditable %}}\n"
    )
    assert f"- uses: actions/checkout@{OLD_SHA} # v1.0.0\n" in actions_up.workflows[0]


def test_each_unique_pin_is_one_step_and_runs_with_min_age(tmp_path, actions_up):
    pin = f"actions/checkout@{OLD_SHA} # v1.0.0"
    first, second = tmp_path / "a.yml", tmp_path / "b.py"
    first.write_text(f"uses: {pin}\nuses: {pin}\n")
    second.write_text(f"X = 'uses: {pin}'\n")

    bump_template_pins([first, second], min_age_days=3)

    assert len(actions_up.calls) == 1
    assert actions_up.calls[0][-2:] == ["--min-age", "3"]
    assert actions_up.workflows[0].count("uses:") == 1


@pytest.mark.usefixtures("actions_up")
def test_unchanged_files_are_not_rewritten(tmp_path):
    bumped, kept = tmp_path / "a.yml", tmp_path / "b.yml"
    bumped.write_text(f"uses: actions/checkout@{OLD_SHA} # v1.0.0\n")
    kept.write_text(f"uses: other/action@{OTHER_SHA} # v2.0.0\n")
    kept_mtime = kept.stat().st_mtime_ns

    changed = bump_template_pins([bumped, kept], min_age_days=3)

    assert changed == [bumped]
    assert kept.stat().st_mtime_ns == kept_mtime


def test_no_pins_means_no_actions_up_run(tmp_path, actions_up):
    template = tmp_path / "plain.yml"
    template.write_text("name: plain\n")

    assert bump_template_pins([template], min_age_days=3) == []
    assert actions_up.calls == []


SHIPPED_TEMPLATES = Path(__file__).parents[3] / "src" / "bakelib" / "space" / "managed"
ANY_SHA = re.compile(r"@(\{% editable \w+ %\})?[0-9a-f]{40} ")


def test_every_pin_in_the_shipped_templates_is_bumped(tmp_path, monkeypatch):
    def bump_all(args: list[str], **_kwargs) -> subprocess.CompletedProcess:
        workflow = next(Path(args[args.index("--dir") + 1]).rglob("*.yml"))
        workflow.write_text(ANY_SHA.sub(f"@{NEW_SHA} ", workflow.read_text()))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("scripts.template_pins.subprocess.run", bump_all)
    copies = []
    for template in sorted(SHIPPED_TEMPLATES.glob("*.yml")):
        copy = tmp_path / template.name
        copy.write_text(template.read_text())
        copies.append(copy)

    bump_template_pins(copies, min_age_days=3)

    pins = [m for copy in copies for m in ANY_SHA.finditer(copy.read_text())]
    assert pins
    assert all(NEW_SHA in m[0] for m in pins)
