import re

import pytest

from scripts.locked_pins import (
    guard_invariants,
    parse_lock_versions,
    relax_locked_pins,
    rewrite_locked_pins,
)

PYPROJECT_TEMPLATE = """\
[project]
name = "bakefile"
version = "0.0.0" # use git tag
dependencies = [
  {base_deps}
]

[project.optional-dependencies]
# Exact pins for tool installs
locked = [
  {locked_pins}
]
"""

LOCK_TEMPLATE = """\
[[package]]
name = "{name}"
version = "{version}"
"""


def make_pyproject(base_deps: list[str], locked_pins: list[str]) -> str:
    base = "\n  ".join(f'"{dep}",' for dep in base_deps)
    locked = "\n  ".join(pin if pin.startswith('"') else f'"{pin}",' for pin in locked_pins)
    return PYPROJECT_TEMPLATE.format(base_deps=base, locked_pins=locked)


def make_lock(packages: list[tuple[str, str]]) -> str:
    return "".join(LOCK_TEMPLATE.format(name=name, version=version) for name, version in packages)


def test_parse_lock_versions_normalizes_names() -> None:
    lock_text = make_lock([("typing_extensions", "4.16.0"), ("typing-extensions", "4.15.0")])

    lock_map = parse_lock_versions(lock_text)

    assert lock_map == {"typing-extensions": {"4.16.0", "4.15.0"}}


def test_pins_rewritten_from_lock() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.26.1"],
        locked_pins=["rich==14.2.0", "typer==0.27.1"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0"), ("typer", "0.27.2")]))

    new_text, changes = rewrite_locked_pins(lock_map, pyproject_text)

    assert '"rich==15.0.0",' in new_text
    assert '"typer==0.27.2",' in new_text
    assert '"rich==14.2.0",' not in new_text
    assert '"typer==0.27.1",' not in new_text
    assert len(changes) == 2


def test_floors_untouched_when_pin_at_or_above_floor() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.27.2"],
        locked_pins=["rich==14.2.0", "typer==0.27.1"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "14.2.0"), ("typer", "0.27.2")]))

    new_text, changes = rewrite_locked_pins(lock_map, pyproject_text)

    assert '"rich>=14.2.0",' in new_text
    assert '"typer>=0.27.2",' in new_text
    assert not [c for c in changes if "floor" in c]


def test_floor_aligned_down_on_drift() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=15.1.0"],
        locked_pins=["rich==15.0.0"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0")]))

    new_text, changes = rewrite_locked_pins(lock_map, pyproject_text)

    assert '"rich>=15.0.0",' in new_text
    assert '"rich>=15.1.0",' not in new_text
    assert [c for c in changes if "floor" in c]


def test_base_dep_missing_from_locked_raises() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "pyyaml>=6.0.3"],
        locked_pins=["rich==15.0.0"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0")]))

    with pytest.raises(ValueError, match="pyyaml missing from \\[locked\\]"):
        rewrite_locked_pins(lock_map, pyproject_text)


def test_transitive_pin_kept_and_updated() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=[
            "shellingham==1.5.4",
            "tomli==2.4.0; python_version < '3.11'",
            "typer==0.27.1",
        ],
    )
    lock_map = parse_lock_versions(
        make_lock(
            [
                ("shellingham", "2.0.0"),
                ("tomli", "2.4.1"),
                ("typer", "0.27.2"),
            ]
        )
    )

    new_text, changes = rewrite_locked_pins(lock_map, pyproject_text)

    assert '"shellingham==2.0.0",' in new_text
    assert "\"tomli==2.4.1; python_version < '3.11'\"," in new_text
    assert "shellingham" in "".join(changes)


def test_multi_version_lock_entry_raises() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=["typer==0.27.1"],
    )
    lock_map = parse_lock_versions(make_lock([("typer", "0.27.1"), ("typer", "0.27.2")]))

    with pytest.raises(ValueError, match=re.escape("typer has multiple versions in uv.lock")):
        rewrite_locked_pins(lock_map, pyproject_text)


def test_locked_pin_missing_from_lock_raises() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=["orjson==3.12.0", "typer==0.27.1"],
    )
    lock_map = parse_lock_versions(make_lock([("typer", "0.27.2")]))

    with pytest.raises(ValueError, match=re.escape("orjson not found in uv.lock")):
        rewrite_locked_pins(lock_map, pyproject_text)


def test_comments_and_markers_preserved() -> None:
    pyproject_text = make_pyproject(
        base_deps=["tomli>=2.0.0; python_version < '3.11'", "typer>=0.26.1"],
        locked_pins=["tomli==2.4.0; python_version < '3.11'", "typer==0.27.1"],
    )
    lock_map = parse_lock_versions(make_lock([("tomli", "2.4.1"), ("typer", "0.27.2")]))

    new_text, _changes = rewrite_locked_pins(lock_map, pyproject_text)

    assert "# use git tag" in new_text
    assert "# Exact pins for tool installs" in new_text
    assert "\"tomli==2.4.1; python_version < '3.11'\"," in new_text
    assert "\"tomli>=2.0.0; python_version < '3.11'\"," in new_text


def test_guard_passes_on_consistent_state() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.26.1"],
        locked_pins=["rich==15.0.0", "typer==0.27.2"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0"), ("typer", "0.27.2")]))

    assert guard_invariants(lock_map, pyproject_text) == []


def test_guard_catches_floor_above_pin() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=15.1.0"],
        locked_pins=["rich==15.0.0"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0")]))

    violations = guard_invariants(lock_map, pyproject_text)

    assert "pin 15.0.0 < floor 15.1.0 for rich" in violations


def test_guard_catches_pin_diverged_from_lock() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=["typer==0.28.0"],
    )
    lock_map = parse_lock_versions(make_lock([("typer", "0.27.2")]))

    violations = guard_invariants(lock_map, pyproject_text)

    assert "pin 0.28.0 != uv.lock version 0.27.2 for typer, run bake update" in violations


def test_guard_catches_non_exact_pin() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=["typer>=0.27.2"],
    )
    lock_map = parse_lock_versions(make_lock([("typer", "0.27.2")]))

    violations = guard_invariants(lock_map, pyproject_text)

    assert "[locked] entry is not an exact pin: typer>=0.27.2" in violations


def test_guard_catches_base_missing_from_locked() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0"],
        locked_pins=["typer==0.27.2"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0"), ("typer", "0.27.2")]))

    violations = guard_invariants(lock_map, pyproject_text)

    assert "base dependency rich missing from [locked]" in violations


def test_guard_catches_multi_version_lock_entry() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=["typer==0.27.2"],
    )
    lock_map = parse_lock_versions(make_lock([("typer", "0.27.1"), ("typer", "0.27.2")]))

    violations = guard_invariants(lock_map, pyproject_text)

    assert "typer has multiple versions in uv.lock: 0.27.1, 0.27.2" in violations


def test_guard_catches_lock_version_below_floor() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.28.0"],
        locked_pins=["typer==0.28.0"],
    )
    lock_map = parse_lock_versions(make_lock([("typer", "0.27.2")]))

    violations = guard_invariants(lock_map, pyproject_text)

    assert "uv.lock version 0.27.2 < floor 0.28.0 for typer" in violations


def test_relax_lifts_non_held_pins_to_base_floor() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.26.1"],
        locked_pins=["rich==15.0.0", "typer==0.27.2"],
    )

    new_text, relaxed = relax_locked_pins(pyproject_text)

    assert relaxed == ["rich", "typer"]
    assert '"rich>=14.2.0",' in new_text
    assert '"typer>=0.26.1",' in new_text
    assert '"rich==15.0.0",' not in new_text
    assert '"typer==0.27.2",' not in new_text


def test_relax_keeps_held_pin_and_comment() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.26.1"],
        locked_pins=['"rich==14.3.4", # hold', "typer==0.27.2"],
    )

    new_text, relaxed = relax_locked_pins(pyproject_text)

    assert relaxed == ["typer"]
    assert '"rich==14.3.4", # hold' in new_text
    assert '"typer>=0.26.1",' in new_text


def test_relax_skips_locked_only_transitive_pins() -> None:
    pyproject_text = make_pyproject(
        base_deps=["typer>=0.26.1"],
        locked_pins=["shellingham==1.5.4", "typer==0.27.2"],
    )

    new_text, relaxed = relax_locked_pins(pyproject_text)

    assert relaxed == ["typer"]
    assert '"shellingham==1.5.4",' in new_text
    assert '"typer>=0.26.1",' in new_text


def test_hold_detection_requires_exact_token() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.26.1"],
        locked_pins=['"rich==14.3.4", # holdme', "typer==0.27.2"],
    )

    _, relaxed = relax_locked_pins(pyproject_text)

    assert relaxed == ["rich", "typer"]


def test_rewrite_skips_held_pin() -> None:
    pyproject_text = make_pyproject(
        base_deps=["rich>=14.2.0", "typer>=0.26.1"],
        locked_pins=['"rich==14.3.4", # hold', "typer==0.27.1"],
    )
    lock_map = parse_lock_versions(make_lock([("rich", "15.0.0"), ("typer", "0.27.2")]))

    new_text, changes = rewrite_locked_pins(lock_map, pyproject_text)

    assert '"rich==14.3.4", # hold' in new_text
    assert '"typer==0.27.2",' in new_text
    assert "rich" not in "".join(changes)


def test_hold_survives_relax_then_rewrite_cycle() -> None:
    base = ["rich>=14.2.0", "typer>=0.26.1"]
    pyproject_text = make_pyproject(
        base_deps=base,
        locked_pins=['"rich==14.3.4", # hold', "typer==0.27.1"],
    )

    relaxed_text, relaxed = relax_locked_pins(pyproject_text)
    assert relaxed == ["typer"]

    # lock resolves: rich capped at 14.3.4 by held pin, typer floats up
    lock_map = parse_lock_versions(make_lock([("rich", "14.3.4"), ("typer", "0.27.2")]))
    final_text, _changes = rewrite_locked_pins(lock_map, relaxed_text)

    assert '"rich==14.3.4", # hold' in final_text
    assert '"typer==0.27.2",' in final_text
    assert guard_invariants(lock_map, final_text) == []
