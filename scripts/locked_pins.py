import re
import sys
from pathlib import Path

import tomlkit
from packaging.version import Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

PYPROJECT_PATH = Path("pyproject.toml")
UV_LOCK_PATH = Path("uv.lock")

_REQUIREMENT_NAME_PATTERN = re.compile(r"^\s*[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?")
_HOLD_PATTERN = re.compile(r"#\s*hold\b")


def _held_locked_names(locked_array_text: str) -> set[str]:
    # tomlkit keeps trailing comments out of item trivia, so detect holds from
    # the rendered array: one requirement per line, `# hold` marks the version
    held: set[str] = set()
    for line in locked_array_text.splitlines():
        if '"' not in line or not _HOLD_PATTERN.search(line):
            continue
        requirement = line.split("#", 1)[0].strip().rstrip(",").strip().strip('"')
        if requirement:
            held.add(_normalize_name(_split_requirement(requirement)[0]))
    return held


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _split_requirement(requirement: str) -> tuple[str, str, str | None]:
    name_and_spec, _, marker = requirement.partition(";")
    name_and_spec = name_and_spec.strip()
    match = _REQUIREMENT_NAME_PATTERN.match(name_and_spec)
    if match is None:
        raise ValueError(f"Cannot parse requirement: {requirement!r}")
    name = match.group(0)
    return name, name_and_spec[match.end() :].strip(), marker.strip() or None


def parse_lock_versions(lock_text: str) -> dict[str, set[str]]:
    lock = tomllib.loads(lock_text)
    versions: dict[str, set[str]] = {}
    for package in lock.get("package", []):
        if "version" in package:
            versions.setdefault(_normalize_name(package["name"]), set()).add(package["version"])
    return versions


def _lock_version(lock_map: dict[str, set[str]], name: str) -> str:
    versions = lock_map.get(_normalize_name(name))
    if not versions:
        raise ValueError(f"{name} not found in uv.lock")
    if len(versions) > 1:
        detail = ", ".join(sorted(versions))
        raise ValueError(f"{name} has multiple versions in uv.lock: {detail}")
    return next(iter(versions))


def relax_locked_pins(pyproject_text: str) -> tuple[str, list[str]]:
    # Lift exact pins down to their base floors so `uv lock --upgrade` can move
    # every dependency. Held pins (marked `# hold`) keep capping resolution.
    doc = tomlkit.parse(pyproject_text)
    base = doc["project"]["dependencies"]
    locked = doc["project"]["optional-dependencies"]["locked"]

    held = _held_locked_names(tomlkit.dumps(locked))
    base_entries = {_normalize_name(_split_requirement(item)[0]): str(item) for item in base}

    relaxed: list[str] = []
    for i, item in enumerate(locked):
        name = _normalize_name(_split_requirement(item)[0])
        if name in held or name not in base_entries:
            continue
        if str(item) != base_entries[name]:
            locked[i] = base_entries[name]
            relaxed.append(name)

    return tomlkit.dumps(doc), relaxed


def locked_pin_specs(pyproject_text: str) -> dict[str, str]:
    locked = tomlkit.parse(pyproject_text)["project"]["optional-dependencies"]["locked"]
    return {
        _normalize_name(_split_requirement(item)[0]): _split_requirement(item)[1] for item in locked
    }


def rewrite_locked_pins(
    lock_map: dict[str, set[str]], pyproject_text: str
) -> tuple[str, list[str]]:
    doc = tomlkit.parse(pyproject_text)
    base = doc["project"]["dependencies"]
    locked = doc["project"]["optional-dependencies"]["locked"]
    changes: list[str] = []

    held = _held_locked_names(tomlkit.dumps(locked))
    locked_names = {_normalize_name(_split_requirement(item)[0]) for item in locked}
    for item in base:
        name = _normalize_name(_split_requirement(item)[0])
        if name not in locked_names:
            raise ValueError(f"base dependency {name} missing from [locked] extra")

    for i, item in enumerate(locked):
        name, _, marker = _split_requirement(item)
        if _normalize_name(name) in held:
            continue
        version = _lock_version(lock_map, name)
        new_item = f"{name}=={version}" + (f"; {marker}" if marker else "")
        if new_item != item:
            changes.append(f"[locked] {name}: {item} -> {new_item}")
        locked[i] = new_item

    for i, item in enumerate(base):
        name, spec, marker = _split_requirement(item)
        if not spec.startswith(">=") or "," in spec or "<" in spec:
            raise ValueError(f"unsupported base constraint for {name}: {spec!r}")
        floor = Version(spec[2:])
        version = Version(_lock_version(lock_map, name))
        if version < floor:
            new_item = f"{name}>={version}" + (f"; {marker}" if marker else "")
            base[i] = new_item
            changes.append(f"[dependencies] {name}: floor {floor} -> {version}")

    return tomlkit.dumps(doc), changes


def guard_invariants(lock_map: dict[str, set[str]], pyproject_text: str) -> list[str]:
    doc = tomlkit.parse(pyproject_text)
    base = list(doc["project"]["dependencies"])
    locked = list(doc["project"]["optional-dependencies"]["locked"])
    violations: list[str] = []

    locked_specs: dict[str, str] = {}
    for item in locked:
        name, spec, _ = _split_requirement(item)
        norm = _normalize_name(name)
        if norm in locked_specs:
            violations.append(f"duplicate [locked] entry: {name}")
            continue
        locked_specs[norm] = spec
        if not spec.startswith("==") or "," in spec:
            violations.append(f"[locked] entry is not an exact pin: {item}")

    for item in base:
        name, spec, _ = _split_requirement(item)
        norm = _normalize_name(name)
        if norm not in locked_specs:
            violations.append(f"base dependency {name} missing from [locked]")
            continue
        if not spec.startswith(">=") or "," in spec or "<" in spec:
            violations.append(f"unsupported base constraint for {name}: {spec!r}")
            continue

        versions = lock_map.get(norm)
        if not versions:
            violations.append(f"{name} not found in uv.lock")
            continue
        if len(versions) > 1:
            detail = ", ".join(sorted(versions))
            violations.append(f"{name} has multiple versions in uv.lock: {detail}")
            continue
        lock_version = Version(next(iter(versions)))
        floor = Version(spec[2:])

        if (
            norm in locked_specs
            and locked_specs[norm].startswith("==")
            and "," not in locked_specs[norm]
        ):
            pin = Version(locked_specs[norm][2:])
            if pin < floor:
                violations.append(f"pin {pin} < floor {floor} for {name}")
            if pin != lock_version:
                violations.append(
                    f"pin {pin} != uv.lock version {lock_version} for {name}, run bake update"
                )
        if lock_version < floor:
            violations.append(f"uv.lock version {lock_version} < floor {floor} for {name}")

    return violations


if __name__ == "__main__":
    lock_versions = parse_lock_versions(UV_LOCK_PATH.read_text())
    issues = guard_invariants(lock_versions, PYPROJECT_PATH.read_text())
    for issue in issues:
        print(f"error: {issue}", file=sys.stderr)
    if issues:
        sys.exit(1)
    print("OK: [locked] pins consistent with base floors and uv.lock")
