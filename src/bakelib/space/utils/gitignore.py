import hashlib
import http.client
import re
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from bakelib.managed_content import ManagedContentError

from . import Fetch

GITHUB_GITIGNORE = "https://github.com/github/gitignore"
RAW_URL = "https://raw.githubusercontent.com/github/gitignore/{sha}/{path}.gitignore"

_START = "# Created from github/gitignore@"
_TEMPLATES = "# Templates: "
_HOW_TO_CHANGE = "# To change the templates, override _get_gitignore_templates() in bakefile.py\n"
_END = "# End of github/gitignore section, sha256:"
# the template's fixed line above its editable block; the section sits before it
_EDITABLE = "\n# (editable)\n"
_COMMIT = re.compile(rf"^{re.escape(_START)}(?P<sha>[0-9a-f]{{40}})$", re.MULTILINE)
_SECTION = re.compile(
    rf"^(?P<digested>{re.escape(_START)}(?P<sha>[0-9a-f]{{40}})\n"
    rf"{re.escape(_TEMPLATES)}(?P<paths>[^\n]*)\n{re.escape(_HOW_TO_CHANGE)}(?:[^\n]*\n)*?)"
    rf"{re.escape(_END)}(?P<digest>[0-9a-f]{{16}})\n",
    re.MULTILINE,
)


class TemplateNotFoundError(ManagedContentError):
    pass


@dataclass(frozen=True)
class Upstream:
    latest_sha: Callable[[], str]
    template: Callable[[str, str], str]


def _latest_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "ls-remote", GITHUB_GITIGNORE, "refs/heads/main"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise ManagedContentError(
            f"could not read the latest commit of {GITHUB_GITIGNORE}: {e}"
        ) from e
    sha = result.stdout.split("\t", 1)[0].strip()
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise ManagedContentError(f"`git ls-remote {GITHUB_GITIGNORE}` gave no commit for main")
    return sha


def _template(sha: str, path: str) -> str:
    url = RAW_URL.format(sha=sha, path=path)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode("utf-8")
    except (OSError, http.client.HTTPException, UnicodeDecodeError) as e:
        if isinstance(e, urllib.error.HTTPError) and e.code == 404:
            raise TemplateNotFoundError(
                f"gitignore template {path!r} is not in github/gitignore ({url} answered 404)"
            ) from e
        raise ManagedContentError(
            f"could not fetch gitignore template {path!r} from {url}: {e}"
        ) from e


GITHUB = Upstream(latest_sha=_latest_sha, template=_template)


@dataclass(frozen=True)
class Section:
    sha: str
    paths: tuple[str, ...]
    text: str
    intact: bool


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _clean(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    # the engine splits lines on CR and other separators, as do editors and pre-commit hooks
    kept = [line for line in lines if len(line.splitlines()) <= 1]
    return "\n".join(kept).strip("\n") + "\n"


def render_section(sha: str, templates: dict[str, str]) -> str:
    paths = sorted(templates)
    body = "".join(f"\n### {path} ###\n{_clean(templates[path])}" for path in paths) + "\n"
    # the digest covers the start lines too, so a hand edit of the commit or the list is caught
    digested = f"{_START}{sha}\n{_TEMPLATES}{', '.join(paths)}\n{_HOW_TO_CHANGE}{body}"
    return f"{digested}{_END}{_digest(digested)}\n"


def read_section(text: str | None) -> Section | None:
    match = _SECTION.search(text or "")
    if match is None:
        return None
    return Section(
        sha=match["sha"],
        paths=tuple(match["paths"].split(", ")),
        text=match[0],
        intact=_digest(match["digested"]) == match["digest"],
    )


def _not_fetched(paths: list[str]) -> str:
    return f"# github/gitignore templates not fetched yet: {', '.join(paths)}; run `bake mc sync`\n"


def _fetch_section(sha: str, paths: list[str], upstream: Upstream, *, kept: bool) -> str:
    try:
        return render_section(sha, {path: upstream.template(sha, path) for path in paths})
    except TemplateNotFoundError as e:
        if not kept:
            raise
        raise ManagedContentError(
            f"{e}; it may have been added after commit {sha}; run `bake mc sync --refresh`"
        ) from e


def stack_section(
    current: str | None, templates: Iterable[str], fetch: Fetch, upstream: Upstream
) -> str:
    paths = sorted(set(templates))
    if not paths:
        return ""
    # a copy of the section inside the editable block, or in a hand file to adopt, is not the cache
    managed, found, _ = (current or "").partition(_EDITABLE)
    managed = f"{managed}\n" if found else ""
    section = read_section(managed)
    if (
        section is not None
        and section.intact
        and section.paths == tuple(paths)
        and fetch is not Fetch.REFRESH
    ):
        return section.text
    if fetch is Fetch.NEVER:
        return _not_fetched(paths)
    # adding a template or repairing a hand edit keeps the other templates at their commit
    commit = _COMMIT.search(managed) if fetch is Fetch.WHEN_NEEDED else None
    sha = commit["sha"] if commit else upstream.latest_sha()
    return _fetch_section(sha, paths, upstream, kept=commit is not None)


def render_lines(lines: Iterable[str]) -> str:
    kept = {line.strip() for line in lines} - {""}
    # a `!` line only re-includes what the lines before it ignored
    ordered = sorted(kept, key=lambda line: (line.startswith("!"), line))
    return "".join(f"{line}\n" for line in ordered)
