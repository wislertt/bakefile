"""Upstream tripwires for the pydantic bugs Bakebook works around.

Each pin reproduces one bug on raw ``BaseModel`` classes — no Bakebook in
the graph, so the workarounds in bake/bakebook/bakebook.py never run and
cannot mask the upstream behavior. ``xfail(strict=True)`` turns an
upstream fix into a loud XPASS: when one fires, remove the pin and
revisit the matching workaround.

- pydantic#11700 (private attrs, declared-order merge) →
  ``_remerge_private_attributes_mro``
- pydantic#13678 (fields, declared-order merge) →
  ``_fix_field_merge_mro``
- pydantic#9992 (model_config, declared-order fold) →
  ``_fix_model_config_mro``

The Bakebook-level parity tests live in test_inheritance.py.
"""

import pytest
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict


@pytest.mark.xfail(
    strict=True,
    reason="pydantic/pydantic#11700 — once this XPasses, upstream fixed the "
    "declared-order private-attr merge: remove this test and revisit "
    "_remerge_private_attributes_mro in bake/bakebook/bakebook.py",
)
def test_pydantic_raw_private_attr_mro_bug_still_present() -> None:
    """Pins the raw pydantic bug; the Bakebook-level fix re-resolves the
    same shape after class creation and cannot signal an upstream fix."""

    class RawBase(BaseModel):
        _knob: str = "base"

    class RawOverride(RawBase):
        _knob: str = "override"

    class RawPlain(RawBase):
        pass

    class RawComposed(RawOverride, RawPlain):
        pass

    assert RawComposed()._knob == "override"


@pytest.mark.xfail(
    strict=True,
    reason="pydantic resolves fields from flattened base snapshots in "
    "declared-base order, so an inherited copy shadows a later base's "
    "override (pydantic/pydantic#13678; kin of #11700, no v2 fix planned). "
    "Once this XPasses, upstream fixed it: remove _fix_field_merge_mro "
    "from bake/bakebook/bakebook.py",
)
def test_pydantic_raw_field_mro_bug_still_present() -> None:
    """Pins the raw pydantic bug; the Bakebook-level fix re-resolves the
    shape after class creation and cannot signal an upstream fix."""

    class RawBase(BaseModel):
        f: str = "base"

    class RawOverride(RawBase):
        f: str = "override"

    class RawPlain(RawBase):
        pass

    class RawSwapped(RawPlain, RawOverride):
        pass

    assert RawSwapped().f == "override"


@pytest.mark.xfail(
    strict=True,
    reason="pydantic folds base model_configs in declared-base order, "
    "last wins, so the later base's value shadows the earlier one's "
    "(pydantic/pydantic#9992, v3 fix planned). Once this XPasses, upstream "
    "fixed it: remove _fix_model_config_mro from bake/bakebook/bakebook.py",
)
def test_pydantic_raw_model_config_mro_bug_still_present() -> None:
    """Pins the raw pydantic bug; the Bakebook-level fix re-resolves the
    same shape after class creation and cannot signal an upstream fix."""

    class RawA(BaseModel):
        model_config = SettingsConfigDict(env_file=".a")

    class RawB(BaseModel):
        model_config = SettingsConfigDict(env_file=".b")

    class RawComposed(RawA, RawB):
        pass

    assert RawComposed.model_config["env_file"] == ".a"
