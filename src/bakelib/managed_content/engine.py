import hashlib
import json
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import cache, cached_property
from importlib import import_module
from importlib.metadata import distributions, packages_distributions
from importlib.resources import files
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Self, cast
from urllib.parse import urlparse
from urllib.request import url2pathname

HEADER = 'managed by bakefile; edit only the parts marked "editable"'
LOCK_FILE = "bake.lock"
REPO_KEY = "repo"
LOCK_VERSION = 1
LOCK_REVISION = 1
LOCK_HINT = f"run `bake mc lock` to rebuild {LOCK_FILE} from the files"
FORCE_HINT = "run `bake mc sync --force` to overwrite it (git diff shows what is dropped)"
FORCE_OR_DETACH_HINT = (
    f"{FORCE_HINT}, or to keep it as is, call `.detach()` on its entry "
    "in `_get_managed_files()` in bakefile.py"
)

_HASH_COMMENT_SUFFIXES = {".yaml", ".yml", ".toml", ".py", ".sh"}
_SLASH_COMMENT_SUFFIXES = {".ts", ".js", ".mjs", ".cjs", ".json5", ".jsonc"}
_IGNORE_FILE = re.compile(r"\.[\w-]*ignore")
_NAME = r"[a-z_][a-z0-9_]*"
_OPEN = re.compile(rf"\{{% editable (?P<name>{_NAME}) %\}}")
_CLOSE = re.compile(rf"\{{% endeditable(?: (?P<name>{_NAME}))? %\}}")
_VALUE = re.compile(rf"\{{\{{ bakefile\.(?P<name>{_NAME}) \}}\}}")
_HOOK = re.compile(rf"^(?P<indent>[ \t]*)\{{% hook (?P<name>{_NAME}) %\}}\n", re.MULTILINE)
_BLOCK_TAG_LINE = re.compile(rf"\{{% (?:editable {_NAME}|endeditable(?: {_NAME})?) %\}}\n")
_TAG_START = re.compile(r"\{%|\{\{-?\s*bakefile\b")
_RAW = "{% raw %}"
_END_RAW = "{% endraw %}"
_GAP = "\x00gap"
_INLINE = "\x01"


class ManagedContentError(Exception):
    pass


@dataclass(frozen=True)
class ManagedFile:
    package: str | None
    name: str
    detached: bool = False
    text: str | None = field(default=None, init=False)
    edited_text: str | None = field(default=None, init=False)

    @classmethod
    def from_text(cls, text: str, *, package: str | None = None, name: str | None = None) -> Self:
        if (package is None) != (name is None):
            raise ManagedContentError(
                "ManagedFile.from_text: give both package and name, or neither"
            )
        return cls(package, name or "")._with(text=normalise(text))

    @property
    def is_repo_template(self) -> bool:
        return self.package is None and self.text is not None

    @property
    def key(self) -> str:
        if self.is_repo_template:
            return REPO_KEY
        return f"{self._package}:{self.name}"

    def key_for(self, path: str) -> str:
        return f"{REPO_KEY}:{path}" if self.is_repo_template else self.key

    @property
    def _package(self) -> str:
        if not self.package:
            raise ManagedContentError(
                f"template {self.name}: give ManagedFile a package, or use ManagedFile.from_text"
            )
        return self.package

    def read_template(self) -> str:
        if self.edited_text is not None:
            return self.edited_text
        if self.text is not None:
            return self.text
        try:
            resource = files(self._package) / "managed" / self.name
        except ModuleNotFoundError as e:
            raise ManagedContentError(
                f"template {self.key}: package {self._package!r} cannot be imported"
            ) from e
        try:
            return normalise(resource.read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise ManagedContentError(
                f"template {self.name}: not found in {self._package}/managed/"
            ) from e

    def insert(self, hook: str, text: str) -> Self:
        source = self.read_template()
        found = template_hooks(self.key, source)
        if hook not in found:
            raise ManagedContentError(f"template {self.key}: there is no template hook {hook!r}")
        text = normalise(text)
        if taken := sorted(_block_names(text) & _block_names(source)):
            raise ManagedContentError(
                f"template {self.key}: an insert at template hook {hook!r} adds editable block "
                f"{taken[0]!r}, which the template already has"
            )
        marker = found[hook]
        indented = "".join(
            # block tags stay at column 0, where the grammar expects them
            line if _BLOCK_TAG_LINE.fullmatch(line) else _indent_lines(line, marker["indent"])
            for line in text.splitlines(keepends=True)
        )
        # above the marker, so a later insert at the same hook lands after this one
        return self._edited(source[: marker.start()] + indented + source[marker.start() :])

    def set_default(self, block: str, text: str) -> Self:
        source = self.read_template()
        opened = [m for m in _OPEN.finditer(source) if m["name"] == block]
        if len(opened) != 1:
            raise ManagedContentError(f"template {self.key}: there is no editable block {block!r}")
        start = opened[0].end()
        closed = _CLOSE.search(source, start)
        if closed is None:
            raise _unclosed_block(self.key, block)
        if hook := _HOOK.search(source[start : closed.start()]):
            raise ManagedContentError(
                f"template {self.key}: editable block {block!r} holds template hook "
                f"{hook['name']!r}, so insert there instead of replacing its default"
            )
        if source[start : start + 1] == "\n":
            start, text = start + 1, normalise(text)
        elif "\n" in text.removesuffix("\n"):
            raise ManagedContentError(
                f"template {self.key}: editable block {block!r} is inline, so its default must "
                f"be one line"
            )
        else:
            text = text.removesuffix("\n")
        return self._edited(source[:start] + text + source[closed.start() :])

    def detach(self) -> Self:
        return self._with(detached=True)

    def _edited(self, source: str) -> Self:
        template_hooks(self.key, source)
        return self._with(edited_text=source)

    def _with(
        self, *, detached: bool = False, text: str | None = None, edited_text: str | None = None
    ) -> Self:
        # text and edited_text are not init fields, so replace() alone would drop them
        copy = replace(self, detached=detached or self.detached)
        object.__setattr__(copy, "text", self.text if text is None else text)
        object.__setattr__(
            copy, "edited_text", self.edited_text if edited_text is None else edited_text
        )
        return copy


def template_hooks(key: str, source: str) -> dict[str, re.Match[str]]:
    found: dict[str, re.Match[str]] = {}
    for match in _HOOK.finditer(source):
        if match["name"] in found:
            raise ManagedContentError(
                f"template {key}: template hook {match['name']!r} appears twice"
            )
        found[match["name"]] = match
    return found


def _block_names(text: str) -> set[str]:
    return {m["name"] for m in _OPEN.finditer(text)}


@cache
def _distribution(package: str) -> str:
    top = package.split(".", 1)[0]
    if found := packages_distributions().get(top):
        return found[0]
    try:
        module = import_module(top)
    except ImportError:
        return top
    # editable installs list no module files, so match the install's source directory
    module_file = getattr(module, "__file__", None)
    if module_file is not None:
        for dist in distributions():
            source = _editable_source(dist.read_text("direct_url.json"))
            if source is not None and Path(module_file).resolve().is_relative_to(source):
                return dist.metadata["Name"]
    return top


def _editable_source(direct_url: str | None) -> Path | None:
    if not direct_url:
        return None
    data = json.loads(direct_url)
    if not data.get("dir_info", {}).get("editable"):
        return None
    url = urlparse(data.get("url", ""))
    return Path(url2pathname(url.path)).resolve() if url.scheme == "file" else None


def comment_header(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.suffix in _HASH_COMMENT_SUFFIXES or _IGNORE_FILE.fullmatch(pure.name):
        return f"# {HEADER}\n"
    if pure.suffix in _SLASH_COMMENT_SUFFIXES:
        return f"// {HEADER}\n"
    if pure.suffix == ".md":
        # an HTML comment is its own Markdown block, and formatters put a blank line after it
        return f"<!-- {HEADER} -->\n\n"
    if pure.suffix == ".json":
        raise ManagedContentError(
            f"{path}: plain .json has no comments for the managed header, use .json5 or .jsonc"
        )
    raise ManagedContentError(f"{path}: unsupported file type for a managed file")


def normalise(text: str) -> str:
    text = text.removeprefix("\ufeff").replace("\r\n", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class EditableBlock:
    name: str
    default: str
    inline: bool


@dataclass(frozen=True)
class BakefileValue:
    name: str
    text: str
    inline: bool


Part = str | EditableBlock | BakefileValue


@dataclass(frozen=True)
class Reading:
    editable: dict[str, str]
    changed_values: tuple[str, ...]


def _describe(part: EditableBlock | BakefileValue) -> str:
    kind = "editable block" if isinstance(part, EditableBlock) else "bakefile value"
    return f"{kind} {part.name!r}"


@dataclass(frozen=True)
class Template:
    key: str
    parts: tuple[Part, ...]

    @cached_property
    def header(self) -> str:
        first = self.parts[0]
        assert isinstance(first, str)
        return first.split("\n", 1)[0]

    @cached_property
    def blocks(self) -> dict[str, EditableBlock]:
        return {p.name: p for p in self.parts if isinstance(p, EditableBlock)}

    @cached_property
    def defaults(self) -> dict[str, str]:
        return {name: e.default for name, e in self.blocks.items()}

    @cached_property
    def _pattern(self) -> re.Pattern[str]:
        pieces: list[str] = []
        for index, p in enumerate(self.parts):
            if isinstance(p, str):
                pieces.append(re.escape(p))
                continue
            group = f"e_{p.name}" if isinstance(p, EditableBlock) else f"v{index}"
            body = r"[^\n]*?" if p.inline else r"(?:[^\n]*\n)*?"
            pieces.append(f"(?P<{group}>{body})")
        return re.compile("".join(pieces))

    def read(self, text: str) -> Reading | None:
        match = self._pattern.fullmatch(text)
        if match is None:
            return None
        return Reading(
            editable={name: match[f"e_{name}"] for name in self.blocks},
            changed_values=tuple(
                p.name
                for index, p in enumerate(self.parts)
                if isinstance(p, BakefileValue) and match[f"v{index}"] != p.text
            ),
        )

    def render(self, contents: Mapping[str, str]) -> str:
        out: list[str] = []
        for part in self.parts:
            if isinstance(part, str):
                out.append(part)
                continue
            if isinstance(part, BakefileValue):
                out.append(part.text)
                continue
            content = contents.get(part.name, part.default)
            if not part.inline and content and not content.endswith("\n"):
                content += "\n"
            out.append(content)
        return "".join(out)

    def equals_defaults_without_header(self, text: str) -> bool:
        # the header may be followed by a blank line, which a hand file would not start with
        body = self.render({}).removeprefix(self.header + "\n")
        return text.lstrip("\n") == body.lstrip("\n")

    def changed(self, contents: Mapping[str, str]) -> dict[str, str]:
        return {
            name: value
            for name, value in contents.items()
            if name in self.blocks and normalise(value) != normalise(self.defaults[name])
        }

    def first_mismatch(self, actual: str) -> str:
        skeleton = "".join(
            p if isinstance(p, str) else _INLINE if p.inline else f"{_GAP}\n" for p in self.parts
        )
        defaults = iter(
            p.default if isinstance(p, EditableBlock) else p.text
            for p in self.parts
            if not isinstance(p, str) and p.inline
        )
        actual_lines = actual.split("\n")[:-1]
        at, gap = 0, False
        for want in skeleton.split("\n")[:-1]:
            if want == _GAP:
                gap = True
                continue
            pattern = re.compile("[^\n]*?".join(re.escape(piece) for piece in want.split(_INLINE)))
            shown = re.sub(_INLINE, lambda _: next(defaults), want)
            found = next(
                (
                    n
                    for n in range(at, len(actual_lines) if gap else min(at + 1, len(actual_lines)))
                    if pattern.fullmatch(actual_lines[n])
                ),
                None,
            )
            if found is None:
                if at >= len(actual_lines):
                    return f"expected '{shown}', but the file ends at line {at}"
                return f"expected '{shown}', but line {at + 1} is '{actual_lines[at]}'"
            at, gap = found + 1, False
        if gap or at >= len(actual_lines):  # pragma: no cover
            return "the file does not match its template"
        return f"expected the end of the file, but line {at + 1} is '{actual_lines[at]}'"


def parse_template(
    key: str, header: str, source: str, values: Mapping[str, object]
) -> tuple[Part, ...]:
    parts: list[Part] = []
    literal, at = header, 0
    opened: re.Match[str] | None = None
    default = ""
    while tag := _TAG_START.search(source, at):
        start = tag.start()
        if opened is None:
            literal += source[at:start]
        else:
            default += source[at:start]
        if source.startswith(_RAW, start):
            end = source.find(_END_RAW, start)
            if end == -1:
                raise ManagedContentError(f"template {key}: `{_RAW}` needs `{_END_RAW}`")
            text = source[start + len(_RAW) : end]
            if opened is None:
                literal += text
            else:
                default += text
            at = end + len(_END_RAW)
            continue
        if value := _VALUE.match(source, start):
            name = value["name"]
            given = _value(key, values, name)
            line_start = source.rfind("\n", 0, start) + 1
            indent = source[line_start:start]
            alone = indent.strip() == "" and source[value.end() :][:1] in ("\n", "")
            if alone:
                text = _indent_lines(given, indent)
                at = value.end() + 1
            else:
                text = given.removesuffix("\n")
                if "\n" in text:
                    raise ManagedContentError(
                        f"template {key}: bakefile value {name!r} has more than one line, "
                        f"so its tag must sit alone on its line"
                    )
                at = value.end()
            if opened is not None:
                default = default.removesuffix(indent) + text if alone else default + text
                continue
            if alone:
                literal = literal.removesuffix(indent)
            parts += [literal, BakefileValue(name=name, text=text, inline=not alone)]
            literal = ""
            continue
        if opened is None:
            if (block_open := _OPEN.match(source, start)) is None:
                raise ManagedContentError(f"template {key}: malformed tag {_near(source, start)}")
            opened, default, at = block_open, "", block_open.end()
            continue
        name = opened["name"]
        closed = _CLOSE.match(source, start)
        if closed is None or closed["name"] not in (None, name):
            if closed is None and _OPEN.match(source, start) is None:
                raise ManagedContentError(f"template {key}: malformed tag {_near(source, start)}")
            raise _unclosed_block(key, name)
        block = (
            source[opened.start() - 1 : opened.start()] in ("\n", "")
            and source[opened.end()] == "\n"
            and source[closed.start() - 1] == "\n"
            and source[closed.end() :][:1] in ("\n", "")
        )
        if block:
            default = default[1:]
            at = closed.end() + 1
        elif "\n" in default:
            raise ManagedContentError(
                f"template {key}: editable block {name!r} must have both tags on their own "
                f"lines (block) or on one line (inline)"
            )
        else:
            at = closed.end()
        parts += [literal, EditableBlock(name=name, default=default, inline=not block)]
        literal, opened = "", None
    if opened is not None:
        raise _unclosed_block(key, opened["name"])
    parts.append(literal + source[at:])
    _check_parts(key, parts)
    return tuple(parts)


def _unclosed_block(key: str, name: str) -> ManagedContentError:
    return ManagedContentError(
        f"template {key}: editable block {name!r} needs `{{% endeditable %}}` to close it"
    )


def _indent_lines(text: str, indent: str) -> str:
    return "".join(f"{indent}{line}\n" if line.strip() else "\n" for line in text.splitlines())


def _near(source: str, start: int) -> str:
    return f"near {source[start : start + 40]!r}"


def _check_parts(key: str, parts: list[Part]) -> None:
    blocks = [p for p in parts if isinstance(p, EditableBlock)]
    # parts alternate fixed text and captures, starting with the header
    for index in range(2, len(parts) - 1, 2):
        if parts[index] == "":
            before = cast("EditableBlock | BakefileValue", parts[index - 1])
            after = cast("EditableBlock | BakefileValue", parts[index + 1])
            raise ManagedContentError(
                f"template {key}: {_describe(after)} needs fixed text between it "
                f"and the {_describe(before)} before it"
            )
    names = [b.name for b in blocks]
    if duplicates := sorted({n for n in names if names.count(n) > 1}):
        raise ManagedContentError(f"template {key}: editable block {duplicates[0]!r} appears twice")


def _value(key: str, values: Mapping[str, object], name: str) -> str:
    if name not in values:
        raise ManagedContentError(
            f"template {key}: bakefile value {name!r} is not among the values the Bakebook gives"
        )
    value = values[name]
    if not isinstance(value, str):
        raise ManagedContentError(
            f"template {key}: bakefile value {name!r} must be text, got {type(value).__name__}"
        )
    return value


def load_templates(
    managed_files: Mapping[str, ManagedFile], values: Mapping[str, object]
) -> dict[str, Template]:
    templates: dict[str, Template] = {}
    for path, managed_file in sorted(managed_files.items()):
        if managed_file.detached:
            continue
        key = managed_file.key_for(path)
        header = comment_header(path)
        source = managed_file.read_template()
        template_hooks(key, source)
        source = _HOOK.sub("", source)
        templates[path] = Template(key=key, parts=parse_template(key, header, source, values))
    return templates


@dataclass
class LockEntry:
    template: str
    hash: str
    editable: dict[str, str] = field(default_factory=dict)

    def matches(self, text: str) -> bool:
        return self.hash == content_hash(text)


def read_lock(root: Path) -> dict[str, LockEntry]:
    lock_path = root / LOCK_FILE
    if not lock_path.is_file():
        return {}
    try:
        data = tomllib.loads(normalise(lock_path.read_bytes().decode("utf-8")))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise ManagedContentError(f"{LOCK_FILE} does not parse ({e}); {LOCK_HINT}") from e
    if data.get("version") != LOCK_VERSION:
        raise ManagedContentError(
            f"{LOCK_FILE}: unsupported version {data.get('version')!r}; {LOCK_HINT}"
        )
    table = data.get("managed-content", {})
    if not isinstance(table, dict):
        raise ManagedContentError(f"{LOCK_FILE}: `managed-content` is not a table; {LOCK_HINT}")
    entries: dict[str, LockEntry] = {}
    for path, entry in table.items():
        if not (
            isinstance(entry, dict)
            and isinstance(entry.get("template"), str)
            and isinstance(entry.get("hash"), str)
        ):
            raise ManagedContentError(
                f"{LOCK_FILE}: entry {path!r} needs string `template` and `hash`; {LOCK_HINT}"
            )
        editable = entry.get("editable", {})
        if not (isinstance(editable, dict) and all(isinstance(v, str) for v in editable.values())):
            raise ManagedContentError(
                f"{LOCK_FILE}: entry {path!r} needs string `editable` values; {LOCK_HINT}"
            )
        if not _is_project_path(path):
            raise ManagedContentError(f"{LOCK_FILE}: {path!r} is outside the project; {LOCK_HINT}")
        entries[path] = LockEntry(template=entry["template"], hash=entry["hash"], editable=editable)
    return entries


def _is_project_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return not (
        pure.is_absolute() or ".." in pure.parts or "\\" in path or PureWindowsPath(path).drive
    )


def _toml_string(value: str) -> str:
    # JSON string escapes are valid TOML basic strings, except DEL must be escaped too
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")


def dump_lock(entries: Mapping[str, LockEntry]) -> str:
    lines = [f"version = {LOCK_VERSION}", f"revision = {LOCK_REVISION}"]
    for path in sorted(entries):
        entry = entries[path]
        lines += [
            "",
            f"[managed-content.{_toml_string(path)}]",
            f"template = {_toml_string(entry.template)}",
            f"hash = {_toml_string(entry.hash)}",
        ]
        lines += [
            f"editable.{name} = {_toml_string(value)}"
            for name, value in sorted(entry.editable.items())
        ]
    return "\n".join(lines) + "\n"


def drop_detached(
    lock: Mapping[str, LockEntry], managed_files: Mapping[str, ManagedFile]
) -> tuple[dict[str, LockEntry], list[str]]:
    detached = {path for path, managed_file in managed_files.items() if managed_file.detached}
    notes = [
        f"{path}: detached, bake no longer manages it; its {LOCK_FILE} entry is dropped"
        for path in sorted(detached & set(lock))
    ]
    return {path: entry for path, entry in lock.items() if path not in detached}, notes


def read_file(root: Path, path: str) -> str | None:
    file_path = root / path
    if not file_path.is_file():
        return None
    try:
        return normalise(file_path.read_bytes().decode("utf-8"))
    except UnicodeDecodeError as e:
        raise ManagedContentError(f"{path}: not UTF-8 text") from e


def _lock_entry(template: Template, text: str, contents: Mapping[str, str]) -> LockEntry:
    return LockEntry(
        template=template.key, hash=content_hash(text), editable=template.changed(contents)
    )


def relock(
    root: Path, templates: Mapping[str, Template], lock: Mapping[str, LockEntry]
) -> dict[str, LockEntry]:
    entries = dict(lock)
    for path, template in templates.items():
        current = read_file(root, path)
        if current is None:
            continue
        entry = lock.get(path)
        if entry is not None and entry.matches(current):
            # unchanged since locked: an untouched block must keep following the defaults
            continue
        if (reading := template.read(current)) is not None:
            entries[path] = _lock_entry(template, current, reading.editable)
    return entries


@dataclass
class Plan:
    writes: dict[str, str] = field(default_factory=dict)
    deletes: list[str] = field(default_factory=list)
    lock: dict[str, LockEntry] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def changes(self) -> list[str]:
        return sorted([*self.writes, *self.deletes])


def plan_sync(
    root: Path,
    templates: Mapping[str, Template],
    lock: Mapping[str, LockEntry],
    *,
    force: bool,
) -> Plan:
    lock = relock(root, templates, lock)
    plan = Plan(lock=dict(lock))
    for path, template in templates.items():
        current = read_file(root, path)
        plan.notes += [f"{path}: {note}" for note in _value_notes(template, current)]
        try:
            found, notes = _block_contents(template, current, lock.get(path), force=force)
        except ManagedContentError as e:
            plan.errors.append(f"{path}: {e}")
            continue
        contents, carry_notes = _carry_over(template, found)
        plan.notes += [f"{path}: {note}" for note in [*notes, *carry_notes]]
        text = template.render(contents)
        plan.lock[path] = _lock_entry(template, text, contents)
        if current != text:
            plan.writes[path] = text
    for path in sorted(set(lock) - set(templates)):
        del plan.lock[path]
        if not (root / path).is_file():
            continue
        if _unchanged_since_locked(root, path, lock[path]):
            plan.deletes.append(path)
        else:
            plan.notes.append(
                f"{path}: kept, changed since bake wrote it and no Space produces it any more; "
                "it is now a hand file"
            )
    return plan


def _unchanged_since_locked(root: Path, path: str, entry: LockEntry) -> bool:
    try:
        current = read_file(root, path)
    except ManagedContentError:
        return False
    return current is not None and entry.matches(current)


def _value_notes(template: Template, current: str | None) -> list[str]:
    reading = template.read(current) if current is not None else None
    if reading is None:
        return []
    return [
        f"bakefile value {name!r} differs from what the Bakebook gives now, rewritten "
        f"(hand edits inside it are not kept)"
        for name in dict.fromkeys(reading.changed_values)
    ]


def _block_contents(
    template: Template, current: str | None, entry: LockEntry | None, *, force: bool
) -> tuple[dict[str, str], list[str]]:
    locked = dict(entry.editable) if entry else {}
    if current is None:
        return locked, []
    if entry is not None and entry.matches(current):
        # unchanged since locked, so the lock holds every changed block: also the upgrade path
        return locked, []
    if not current.startswith(template.header + "\n"):
        if entry is not None:
            if force:
                return locked, []
            raise ManagedContentError(
                f"managed header missing on a file {LOCK_FILE} manages; {FORCE_HINT}"
            )
        if template.equals_defaults_without_header(current):
            return {}, ["taken over, it already equals what bake writes"]
        if force:
            return {}, []
        raise ManagedContentError(f"exists without the managed header; {FORCE_OR_DETACH_HINT}")
    if force:
        return locked, []
    mismatch = template.first_mismatch(current)
    if entry is None:
        raise ManagedContentError(f"{mismatch}; {FORCE_OR_DETACH_HINT}")
    owner = entry.template.split(":", 1)[0]
    if owner == REPO_KEY:
        upgrade = "If its template in bakefile.py changed since, restore the previous one"
    else:
        dist = _distribution(owner)
        upgrade = f"If {dist} was upgraded since, reinstall the previous {dist}"
    raise ManagedContentError(
        f"{mismatch}; the file changed since {LOCK_FILE} was written. {upgrade} "
        f"and run `bake mc lock` first; or {FORCE_OR_DETACH_HINT}"
    )


def _carry_over(template: Template, found: Mapping[str, str]) -> tuple[dict[str, str], list[str]]:
    contents: dict[str, str] = {}
    notes: list[str] = []
    for name, content in sorted(found.items()):
        block = template.blocks.get(name)
        if block is None:
            notes.append(
                f"editable block {name!r} is no longer in the template, its content is dropped"
            )
            continue
        if block.inline:
            content = content.removesuffix("\n")
            if "\n" in content:
                notes.append(f"editable block {name!r} is now inline, its content is dropped")
                continue
        contents[name] = content
    return contents, notes


def apply_plan(root: Path, plan: Plan) -> None:
    for path, text in plan.writes.items():
        file_path = root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(text.encode())
    for path in plan.deletes:
        (root / path).unlink()


def write_lock(root: Path, entries: Mapping[str, LockEntry]) -> bool:
    lock_path = root / LOCK_FILE
    text = dump_lock(entries)
    old = read_file(root, LOCK_FILE)
    if old == text or (old is None and not entries):
        return False
    lock_path.write_bytes(text.encode())
    return True
