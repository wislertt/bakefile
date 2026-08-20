[![tests](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=tests&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![release](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=release&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![quality-gate-status](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![security-rating](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![codecov](https://codecov.io/gh/wislertt/bakefile/graph/badge.svg?token=G0ZRDBGAJB)](https://codecov.io/gh/wislertt/bakefile)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&color=green)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json&color=green)](https://github.com/astral-sh/ty)
[![pypi](https://img.shields.io/pypi/v/bakefile.svg?color=blue)](https://pypi.python.org/pypi/bakefile)
[![status](https://img.shields.io/pypi/status/bakefile)](https://pypi.python.org/pypi/bakefile)
[![license](https://img.shields.io/pypi/l/bakefile)](https://pypi.python.org/pypi/bakefile)
[![downloads](https://static.pepy.tech/personalized-badge/bakefile?period=total&units=international_system&left_color=grey&right_color=blue&left_text=pypi%20downloads)](https://pepy.tech/projects/bakefile)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?logo=python)](https://github.com/wislertt/bakefile/)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/wislertt/bakefile@main/docs/img/brand/bakefile-lockup-dark.svg">
    <img src="https://cdn.jsdelivr.net/gh/wislertt/bakefile@main/docs/img/brand/bakefile-lockup.svg" width="360" alt="bakefile logo">
  </picture>
</p>

# bakefile

An OOP task runner. Write tasks once, reuse everywhere. Like a Makefile, but reusable and in Python.

Documentation: **[bakefile.wisl.dev](https://bakefile.wisl.dev)**

## Why bakefile?

- **Reusable** - Makefile and Justfile work well, but reusing tasks across projects is hard. bakefile makes tasks Python class methods, so you inherit and share them like any other code.
- **Python** - Write Python instead of a DSL. Real language features, type checking with ruff and ty, and the rest of Python's tooling. `ctx.run()` still handles normal CLI commands through subprocess.
- **Language-agnostic** - Tasks are Python, but the commands they run can target any language (Go, Rust, JS, etc.).

Tasks are class methods you inherit, override, and compose, so reusable task libraries ([bakelib Spaces](https://bakefile.wisl.dev/bakelib/spaces)) just work. bakefile is new, built on modern typed Python (Typer + Pydantic). **Production-proven:** I run it daily at my company.

See how bakefile compares to Make, Just, Task, mise, and Invoke in [Why bakefile](https://bakefile.wisl.dev/getting-started/why-bakefile).

## Installation

```bash
pip install bakefile
```

Or via uv:

```bash
uv tool install bakefile
```

## Quick Start

```python
from bake import Bakebook, command, console


class MyBakebook(Bakebook):
    @command()
    def build(self) -> None:
        console.echo("Building...")
        self.ctx.run("cargo build")


bakebook = MyBakebook()
```

```bash
bake build
```

Generate a bakefile with `bakefile init`, or start from the [simple example](https://bakefile.wisl.dev/examples/simple). Full walkthrough in the [quickstart](https://bakefile.wisl.dev/getting-started/quickstart).

## Documentation

Full documentation lives at [bakefile.wisl.dev](https://bakefile.wisl.dev):

- [Why bakefile](https://bakefile.wisl.dev/getting-started/why-bakefile) - comparison with Make, Just, Task, mise, and Invoke
- [Concepts](https://bakefile.wisl.dev/concepts/bakebook) - Bakebook, commands, context, PEP 723
- [Usage](https://bakefile.wisl.dev/usage/logging) - logging, settings
- [CLI reference](https://bakefile.wisl.dev/cli/bake) - `bake` and `bakefile`
- [bakelib](https://bakefile.wisl.dev/bakelib/spaces) - Spaces, environments, cache, secrets
- [Examples](https://bakefile.wisl.dev/examples/simple) and [troubleshooting](https://bakefile.wisl.dev/troubleshooting)

## Development

```bash
git clone https://github.com/wislertt/bakefile.git
cd bakefile

uv tool install bakefile

bake setup-dev        # Setup development environment (macOS only)
bake assert-setup-dev # Verify the setup is correct

bake test             # Unit tests (fast)
bake test-integration # Integration tests (slow, real subprocess)
bake lint             # prettier, toml-sort, ruff format, ruff check, ty, deptry
```

`bake setup-dev` only supports macOS. On other platforms, run `bake --dry-run setup-dev` to see the commands and follow platform-specific alternatives.

The project uses [uv](https://github.com/astral-sh/uv) for dependency management.

## Contributing

Contributions are welcome. See [CLAUDE.md](/.claude/CLAUDE.md) for development guidelines, including project structure, testing conventions, and the development workflow.

## Author

Wisaroot Lertthaweedech – [wisl.dev](https://wisl.dev)

## License

Licensed under the Apache License 2.0. See [LICENSE](/LICENSE) for the full text.

The wordmark in `docs/img/brand/` uses outlined paths from [Shantell Sans](https://fonts.google.com/specimen/Shantell+Sans), licensed under the [SIL Open Font License 1.1](https://openfontlicense.org/open-font-license-official-text/).
