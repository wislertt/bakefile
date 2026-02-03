[![tests](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=tests&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![release](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=release&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![quality-gate-status](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![security-rating](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![codecov](https://codecov.io/gh/wislertt/bakefile/graph/badge.svg?token=G0ZRDBGAJB)](https://codecov.io/gh/wislertt/bakefile)
[![pypi](https://img.shields.io/pypi/v/bakefile.svg?color=blue)](https://pypi.python.org/pypi/bakefile)
[![downloads](https://static.pepy.tech/personalized-badge/bakefile?period=total&units=international_system&left_color=grey&right_color=blue&left_text=pypi%20downloads)](https://pepy.tech/projects/bakefile)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?logo=python)](https://github.com/wislertt/bakefile/)

# bakefile

An OOP task runner in Python. Like a Makefile, but with tasks as Python class methods—so you can inherit, compose, and reuse them across projects.

## Why bakefile?

- **Reusable** - Makefile/Justfile work well, but reusing tasks across projects is hard. bakefile uses OOP class methods—inherit, compose, and share them
- **Python** - Use Python instead of DSL syntax. Access the full ecosystem with Python's language features, tooling, and type safety (ruff/ty)—with subprocess support for normal CLI commands
- **Language-agnostic** - Write tasks in Python, run commands for any language (Go, Rust, JS, etc.)
