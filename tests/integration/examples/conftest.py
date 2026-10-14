import os
import subprocess
import sys

import pytest


@pytest.fixture(scope="session", autouse=True)
def pin_brew_formulas_on_ci() -> None:
    if not (os.environ.get("GITHUB_ACTIONS") == "true" and sys.platform == "darwin"):
        return
    # setup-dev runs `brew upgrade --yes` over the runner's ~100 preinstalled
    # formulas. One transient upstream download failure (e.g. a deleted release
    # asset) fails the whole test. Pinned formulas are skipped by brew upgrade
    # natively, so the real brew chain still runs but upgrades nothing.
    result = subprocess.run(
        ["brew", "list", "--formula"], capture_output=True, text=True, check=True
    )
    formulas = result.stdout.split()
    if formulas:
        subprocess.run(["brew", "pin", *formulas], check=True)
