"""Inheritance must resolve exactly like native Python.

Every attribute kind a bakebook class can carry (pydantic fields, private
attrs, ClassVars, methods, @command registrations, model_config keys) must
resolve through multiple inheritance the way plain Python classes resolve
attributes: first hit in the MRO wins, regardless of declared-base order.

pydantic v2 instead merges flattened field and private-attr snapshots and
config keys in declared-base order (pydantic#13678, pydantic#11700,
pydantic#9992, no v2 fix planned), so Bakebook re-resolves them after
class creation via _fix_field_merge_mro, _remerge_private_attributes_mro,
and _fix_model_config_mro (bake/bakebook/bakebook.py). These tests hold
that machinery to native parity: each test builds a plain-class mirror of
the same inheritance graph and asserts the bakebook and the mirror agree,
value for value, in both base orders.

One test func = one inheritance pattern, and its graph carries every
attribute kind (field, private attr, ClassVar, method, @command,
model_config key, plus a default_factory field where one fits). The
pattern is what can be mis-resolved, so the coverage matrix (pattern by
kind) is structural: a pattern func cannot exist without declaring all
kinds. Three categories stay separate: kind flips (the flip is the
pattern), generics (machinery pins — the alias hazard is field-specific,
so all-kind asserts there would be vacuous), and non-pattern edges
(instance assignment, remerge guards). Tests group into one test class
per pattern family — parallel branches, shared parent with an overriding
branch (the bug shape), diamond, chains, redeclaration, kind flips,
generics, non-pattern edges — and each class docstring explains its
family.

pydantic-only surfaces (env sources, validators, JSON schema, command
registration, required-ness, typevars) are asserted directly inside the
pattern func they apply to. Mixin composition shapes live in
test_inheritance_mixin.py. The raw-pydantic xfail pins tracking the
upstream bugs live in test_inheritance_upstream_pins.py: when one
XPasses, pydantic fixed it and the corresponding workaround in
bakebook.py can be revisited.
"""

import types
from typing import Annotated, ClassVar, Generic, TypeVar

import pytest
from pydantic import BaseModel, Field, PrivateAttr, ValidationError, field_validator
from pydantic_settings import SettingsConfigDict

from bake import Bakebook, command
from bake.bakebook.bakebook import _fix_field_merge_mro, _remerge_private_attributes_mro
from tests.unit.bake.bakebook.utils import ExpectedCommand, assert_commands

E = TypeVar("E")


class TestParallelBranches:
    """
    Parallel branches: independent bases, no shared bakebook parent.
    """

    def test_parallel_branches_compose(self) -> None:
        # Disjoint names compose from both branches, every kind. Disjoint
        # model_config keys both survive too (pydantic#9992's fold would drop
        # the earlier base's key — every BaseSettings config dict materializes
        # the other key's default, so even "disjoint" declarations collide on
        # raw pydantic; the fix re-resolves per key).
        class BranchOne(Bakebook):
            model_config = SettingsConfigDict(env_file=".one")

            field1: str = "value1"
            _secret1: str = "secret1"
            mode1: ClassVar[str] = "one-mode"

            @command()
            def action1(self) -> str:
                return "action1"

            def describe1(self) -> str:
                return "describe1"

        class BranchTwo(Bakebook):
            model_config = SettingsConfigDict(case_sensitive=True)

            field2: Annotated[list[str], Field(default_factory=lambda: ["web", "api"])]
            _secret2: str = "secret2"
            mode2: ClassVar[str] = "two-mode"

            @command()
            def action2(self) -> str:
                return "action2"

            def describe2(self) -> str:
                return "describe2"

        class MyBakebook(BranchOne, BranchTwo):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeOne:
            field1 = "value1"
            _secret1 = "secret1"
            mode1 = "one-mode"

            def describe1(self) -> str:
                return "describe1"

        class NativeTwo:
            field2: ClassVar[list[str]] = ["web", "api"]
            _secret2 = "secret2"
            mode2 = "two-mode"

            def describe2(self) -> str:
                return "describe2"

        class NativeCombined(NativeOne, NativeTwo):
            pass

        # The kwargs path (pydantic-specific) still initializes both branches.
        bakebook = MyBakebook(field1="custom1", field2=["custom2"])
        assert bakebook.field1 == "custom1"
        assert bakebook.field2 == ["custom2"]

        native = NativeCombined()
        assert MyBakebook().field1 == native.field1 == "value1"
        assert MyBakebook().field2 == native.field2 == ["web", "api"]
        assert MyBakebook()._secret1 == native._secret1 == "secret1"
        assert MyBakebook()._secret2 == native._secret2 == "secret2"
        assert MyBakebook.mode1 == NativeCombined.mode1 == "one-mode"
        assert MyBakebook.mode2 == NativeCombined.mode2 == "two-mode"
        assert MyBakebook().describe1() == native.describe1() == "describe1"
        assert MyBakebook().describe2() == native.describe2() == "describe2"

        assert_commands(
            MyBakebook(),
            {
                "action1": ExpectedCommand(
                    name="action1", command_type=types.MethodType, output="action1"
                ),
                "action2": ExpectedCommand(
                    name="action2", command_type=types.MethodType, output="action2"
                ),
            },
            msg="Commands from both parallel branches register",
        )

        assert MyBakebook.model_config["env_file"] == ".one"
        assert MyBakebook.model_config["case_sensitive"] is True
        assert MyBakebook.model_config["extra"] == "ignore"

    def test_parallel_branch_conflicts_resolve_mro(self) -> None:
        # Same names on both branches, every kind: first MRO hit wins, in both
        # base orders. Identical redeclarations on both branches resolve too.
        class LeftBakebook(Bakebook):
            model_config = SettingsConfigDict(env_file=".left")

            value: str = "left"
            _value: str = "left"
            mode: ClassVar[str] = "left-mode"

            @command()
            def run(self) -> str:
                return "run_left"

            def describe(self) -> str:
                return "describe_left"

        class RightBakebook(Bakebook):
            model_config = SettingsConfigDict(env_file=".right")

            value: str = "right"
            _value: str = "right"
            mode: ClassVar[str] = "right-mode"

            @command()
            def run(self) -> str:
                return "run_right"

            def describe(self) -> str:
                return "describe_right"

        class LeftFirst(LeftBakebook, RightBakebook):
            pass

        class RightFirst(RightBakebook, LeftBakebook):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeLeft:
            value = "left"
            _value = "left"
            mode = "left-mode"

            def run(self) -> str:
                return "run_left"

            def describe(self) -> str:
                return "describe_left"

        class NativeRight:
            value = "right"
            _value = "right"
            mode = "right-mode"

            def run(self) -> str:
                return "run_right"

            def describe(self) -> str:
                return "describe_right"

        class NativeLeftFirst(NativeLeft, NativeRight):
            pass

        class NativeRightFirst(NativeRight, NativeLeft):
            pass

        left_first = LeftFirst()
        assert left_first.value == NativeLeftFirst().value == "left"
        assert left_first._value == NativeLeftFirst()._value == "left"
        assert LeftFirst.mode == NativeLeftFirst.mode == "left-mode"
        assert left_first.describe() == NativeLeftFirst().describe() == "describe_left"
        assert left_first.run() == NativeLeftFirst().run() == "run_left"
        assert LeftFirst.model_config["env_file"] == ".left"

        right_first = RightFirst()
        assert right_first.value == NativeRightFirst().value == "right"
        assert right_first._value == NativeRightFirst()._value == "right"
        assert RightFirst.mode == NativeRightFirst.mode == "right-mode"
        assert right_first.describe() == NativeRightFirst().describe() == "describe_right"
        assert right_first.run() == NativeRightFirst().run() == "run_right"
        assert RightFirst.model_config["env_file"] == ".right"

        assert_commands(
            left_first,
            {
                "run": ExpectedCommand(
                    name="run", command_type=types.MethodType, output="run_left"
                ),
            },
            msg="Left first - leftmost parent wins",
        )
        assert_commands(
            right_first,
            {
                "run": ExpectedCommand(
                    name="run", command_type=types.MethodType, output="run_right"
                ),
            },
            msg="Right first - leftmost parent wins",
        )

        # Identical redeclarations on both branches: either order resolves.
        class SameLeft(LeftBakebook):
            model_config = SettingsConfigDict(env_file=".same")

            value: str = "same"
            _value: str = "same"
            mode: ClassVar[str] = "same-mode"

            @command()
            def run(self) -> str:
                return "run_same"

            def describe(self) -> str:
                return "describe_same"

        class SameRight(RightBakebook):
            model_config = SettingsConfigDict(env_file=".same")

            value: str = "same"
            _value: str = "same"
            mode: ClassVar[str] = "same-mode"

            @command()
            def run(self) -> str:
                return "run_same"

            def describe(self) -> str:
                return "describe_same"

        class Identical(SameLeft, SameRight):
            pass

        bakebook = Identical()
        assert bakebook.value == "same"
        assert bakebook._value == "same"
        assert Identical.mode == "same-mode"
        assert bakebook.run() == "run_same"
        assert bakebook.describe() == "describe_same"

    def test_disjoint_config_keys_match_raw_pydantic(self) -> None:
        # Disjoint model_config keys resolve by union on raw pydantic
        # (BaseModel never materializes settings defaults, so the keys stay
        # disjoint); the fix reproduces that exact answer. Same-key conflicts
        # are the one place raw pydantic diverges — declared-order fold,
        # pydantic#9992, pinned raw in test_inheritance_upstream_pins.py —
        # so this parity oracle stays disjoint-keys only.
        class BranchOne(Bakebook):
            model_config = SettingsConfigDict(env_file=".one")

        class BranchTwo(Bakebook):
            model_config = SettingsConfigDict(case_sensitive=True)

        class Combined(BranchOne, BranchTwo):
            pass

        class RawOne(BaseModel):
            model_config = SettingsConfigDict(env_file=".one")

        class RawTwo(BaseModel):
            model_config = SettingsConfigDict(case_sensitive=True)

        class RawCombined(RawOne, RawTwo):
            pass

        # BaseModel never materializes undeclared defaults into the dict
        # (BaseSettings materializes "extra"), so only declared keys compare.
        # Both sides pin the concrete value too — equality alone could pass
        # with the same wrong answer on both.
        assert Combined.model_config["env_file"] == RawCombined.model_config["env_file"] == ".one"
        assert (
            Combined.model_config["case_sensitive"]
            is RawCombined.model_config["case_sensitive"]
            is True
        )


class TestSharedParentOverride:
    """
    Shared parent, one branch overrides: the bug shape (pydantic#13678,
    pydantic#11700, pydantic#9992). A sibling that merely inherits must not
    shadow the overriding branch, in either base order.
    """

    def test_shared_parent_override_all_kinds_resolves_mro(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Every attr kind on one graph: field, factory field, private attr
        # (annotated, factory, and unannotated), ClassVar, method, @command,
        # property, model_config key. Plus the pydantic-only surfaces: env
        # source, declarer-chain validators, regenerated schema, kwargs path.
        base_factory = Annotated[str, Field(default_factory=lambda: "base-factory")]
        override_factory = Annotated[str, Field(default_factory=lambda: "override-factory")]

        class MatrixBase(Bakebook):
            model_config = SettingsConfigDict(env_file=".matrix-base")

            plain_field: str = "base-field"
            tagged: str = "base-tag"
            factory_field: base_factory
            class_var: ClassVar[str] = "base-classvar"
            _knob: str = "base-default"
            _factory_knob: str = PrivateAttr(default_factory=lambda: "base-factory")
            _pflag = PrivateAttr(default="pf-base")

            @field_validator("tagged", mode="after")
            @classmethod
            def _tag_base(cls, v: str) -> str:
                return v + "/base"

            @command()
            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

            dial: ClassVar[str] = "base-dial"

        class MatrixOverride(MatrixBase):
            model_config = SettingsConfigDict(env_file=".matrix-override")

            plain_field: str = "override-field"
            tagged: str = "override-tag"
            factory_field: override_factory
            class_var: ClassVar[str] = "override-classvar"
            _knob: str = "override"
            _factory_knob: str = PrivateAttr(default_factory=lambda: "override-factory")
            _pflag = PrivateAttr(default="pf-override")

            @field_validator("tagged", mode="after")
            @classmethod
            def _tag_override(cls, v: str) -> str:
                return v + "/override"

            @command()
            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

            @property
            def dial(self) -> str:  # ty: ignore[invalid-attribute-override]
                return "override-dial"

        class MatrixPlain(MatrixBase):
            pass

        class Composed(MatrixOverride, MatrixPlain):
            pass

        class Swapped(MatrixPlain, MatrixOverride):
            pass

        # Native mirror of the same shape resolves via the MRO. Factories'
        # products stand in as plain defaults.
        class NativeBase:
            plain_field = "base-field"
            factory_field = "base-factory"
            class_var = "base-classvar"
            _knob = "base-default"
            _factory_knob = "base-factory"
            _pflag = "pf-base"

            def method(self) -> str:
                return "base-method"

            dial = "base-dial"

        class NativeOverride(NativeBase):
            plain_field = "override-field"
            factory_field = "override-factory"
            class_var = "override-classvar"
            _knob = "override"
            _factory_knob = "override-factory"
            _pflag = "pf-override"

            def method(self) -> str:
                return "override-method"

            @property
            def dial(self) -> str:
                return "override-dial"

        class NativePlain(NativeBase):
            pass

        class NativeComposed(NativeOverride, NativePlain):
            pass

        class NativeSwapped(NativePlain, NativeOverride):
            pass

        for bakebook, native in ((Composed(), NativeComposed()), (Swapped(), NativeSwapped())):
            label = type(bakebook).__name__
            assert bakebook.plain_field == native.plain_field == "override-field", label
            assert bakebook.factory_field == native.factory_field == "override-factory", label
            assert bakebook.class_var == native.class_var == "override-classvar", label
            assert bakebook._knob == native._knob == "override", label
            assert bakebook._factory_knob == native._factory_knob == "override-factory", label
            assert bakebook._pflag == native._pflag == "pf-override", label
            assert bakebook.method() == native.method() == "override-method", label
            assert bakebook.dial == native.dial == "override-dial", label
            assert bakebook.cmd() == "override-cmd", label
            assert type(bakebook).model_config["env_file"] == ".matrix-override", label

            assert_commands(
                bakebook,
                {
                    "cmd": ExpectedCommand(
                        name="cmd", command_type=types.MethodType, output="override-cmd"
                    ),
                },
                msg=f"{label}: marked method registration follows MRO",
            )

        # The swapped FieldInfo is the declarer's own object.
        assert (
            Composed.__pydantic_fields__["plain_field"]
            is (MatrixOverride.__pydantic_fields__["plain_field"])
        )

        # The kwargs path (pydantic-specific) still initializes the fixed field.
        assert Swapped(plain_field="from-kwargs").plain_field == "from-kwargs"

        # The rebuild keeps the settings-source path: env vars still win.
        monkeypatch.setenv("PLAIN_FIELD", "from-env")
        assert Composed().plain_field == "from-env"

        # Declarer-chain validators survive the rebuild and still run (defaults
        # are not validated, so exercise the input path).
        assert Composed(tagged="from-kwargs").tagged == "from-kwargs/base/override"
        assert Swapped(tagged="from-kwargs").tagged == "from-kwargs/base/override"

        # The regenerated core schema carries the declarer's default, not the
        # inherited copy's.
        assert (
            Composed.model_json_schema()["properties"]["plain_field"]["default"] == "override-field"
        )


class TestDiamond:
    """
    Diamond: the shared parent appears once in the MRO and is the single
    declarer of its names.
    """

    def test_diamond_all_kinds_resolves_mro(self) -> None:
        r"""        A
                   / \
                  B   C
                   \ /
                    D
        """

        class BaseA(Bakebook):
            model_config = SettingsConfigDict(env_file=".a")

            a_value: str = "from_A"
            a_list: Annotated[list[str], Field(default_factory=lambda: ["from_A"])]
            _a_secret: str = "from_A"
            mode: ClassVar[str] = "A-mode"

            @command()
            def run(self) -> str:
                return "A"

            def describe(self) -> str:
                return "A"

        class LeftB(BaseA):
            b_value: str = "from_B"

        class RightB(BaseA):
            c_value: str = "from_C"

        class DiamondBakebook(LeftB, RightB):
            pass

        bakebook = DiamondBakebook()

        # Native mirror of the same shape resolves via the MRO.
        class NativeBaseA:
            a_value = "from_A"
            a_list: ClassVar[list[str]] = ["from_A"]
            _a_secret = "from_A"
            mode = "A-mode"

            def run(self) -> str:
                return "A"

            def describe(self) -> str:
                return "A"

        class NativeLeftB(NativeBaseA):
            b_value = "from_B"

        class NativeRightB(NativeBaseA):
            c_value = "from_C"

        class NativeDiamond(NativeLeftB, NativeRightB):
            pass

        native = NativeDiamond()
        assert bakebook.a_value == native.a_value == "from_A"
        assert bakebook.a_list == native.a_list == ["from_A"]
        assert bakebook.b_value == native.b_value == "from_B"
        assert bakebook.c_value == native.c_value == "from_C"
        assert bakebook._a_secret == native._a_secret == "from_A"
        assert bakebook.mode == native.mode == "A-mode"
        assert bakebook.run() == native.run() == "A"
        assert bakebook.describe() == native.describe() == "A"
        assert DiamondBakebook.model_config["env_file"] == ".a"

        mro_names = [
            cls.__name__
            for cls in DiamondBakebook.__mro__
            if cls.__name__ not in ("object", "BaseModel")
        ]
        assert mro_names.count("BaseA") == 1

        assert_commands(
            bakebook,
            {
                "run": ExpectedCommand(name="run", command_type=types.MethodType, output="A"),
            },
            msg="Diamond inheritance - BaseA appears once",
        )


class TestChains:
    """
    Chains: single-inheritance depth, redundant parents, skipped
    intermediates, concrete branches composed, cooperative super(),
    and composed bases composed again (nested composition).
    """

    def test_deep_chain_all_kinds_resolves_mro(self) -> None:
        # Every kind down a single-inheritance chain, with cooperative super()
        # pipelines and an undecorated @command override at the bottom (the
        # parent's registration survives it).
        class Level1(Bakebook):
            model_config = SettingsConfigDict(env_file=".l1")

            level1_field: str = "level1"
            parts: Annotated[list[str], Field(default_factory=lambda: ["l1"])]
            _level: str = "level1"
            mode: ClassVar[str] = "m1"

            @command()
            def action(self) -> str:
                return "level1"

            def pipeline(self) -> list[str]:
                return ["level1"]

        class Level2(Level1):
            level2_field: str = "level2"
            _level: str = "level2"
            mode: ClassVar[str] = "m2"

            @command()
            def action(self) -> str:
                return "level2"

            def pipeline(self) -> list[str]:
                return ["level2", *super().pipeline()]

        class Level3(Level2):
            level3_field: str = "level3"
            _level: str = "level3"

            def action(self) -> str:
                return "level3"

            def describe(self) -> str:
                return "d3"

            def pipeline(self) -> list[str]:
                return ["level3", *super().pipeline()]

        class FinalBakebook(Level3):
            pass

        bakebook = FinalBakebook()

        # Native mirror of the same shape resolves via the MRO.
        class NativeLevel1:
            level1_field = "level1"
            parts: ClassVar[list[str]] = ["l1"]
            _level = "level1"
            mode = "m1"

            def action(self) -> str:
                return "level1"

            def pipeline(self) -> list[str]:
                return ["level1"]

        class NativeLevel2(NativeLevel1):
            level2_field = "level2"
            _level = "level2"
            mode = "m2"

            def action(self) -> str:
                return "level2"

            def pipeline(self) -> list[str]:
                return ["level2", *super().pipeline()]

        class NativeLevel3(NativeLevel2):
            level3_field = "level3"
            _level = "level3"

            def action(self) -> str:
                return "level3"

            def describe(self) -> str:
                return "d3"

            def pipeline(self) -> list[str]:
                return ["level3", *super().pipeline()]

        class NativeFinal(NativeLevel3):
            pass

        native = NativeFinal()
        assert bakebook.level1_field == native.level1_field == "level1"
        assert bakebook.parts == native.parts == ["l1"]
        assert bakebook.level2_field == native.level2_field == "level2"
        assert bakebook.level3_field == native.level3_field == "level3"
        assert bakebook._level == native._level == "level3"
        assert bakebook.mode == native.mode == "m2"
        assert bakebook.action() == native.action() == "level3"
        assert bakebook.describe() == native.describe() == "d3"
        assert bakebook.pipeline() == native.pipeline() == ["level3", "level2", "level1"]
        assert FinalBakebook.model_config["env_file"] == ".l1"

        # The undecorated override keeps the parent's registration, once.
        assert len(bakebook._app.registered_commands) == 1

        assert_commands(
            bakebook,
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="level3"
                ),
            },
            msg="Deep inheritance chain",
        )

        # Redundant parents restated in declared order: same resolution.
        class FinalBakebook2(Level3, Level2, Level1):
            pass

        bakebook2 = FinalBakebook2()

        class NativeFinal2(NativeLevel3, NativeLevel2, NativeLevel1):
            pass

        native2 = NativeFinal2()
        assert bakebook2.level1_field == native2.level1_field == "level1"
        assert bakebook2.parts == native2.parts == ["l1"]
        assert bakebook2.level2_field == native2.level2_field == "level2"
        assert bakebook2.level3_field == native2.level3_field == "level3"
        assert bakebook2._level == native2._level == "level3"
        assert bakebook2.mode == native2.mode == "m2"
        assert bakebook2.action() == native2.action() == "level3"
        assert bakebook2.pipeline() == native2.pipeline() == ["level3", "level2", "level1"]

        assert_commands(
            bakebook2,
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="level3"
                ),
            },
            msg="Deep inheritance with redundant parents - same result",
        )

    def test_skip_intermediate_parent(self) -> None:
        # (Level3, Level1): Level2 stays in the MRO between them either way.
        class Level1(Bakebook):
            model_config = SettingsConfigDict(env_file=".sl1")

            level1_field: str = "level1"
            serial: Annotated[list[str], Field(default_factory=lambda: ["s1"])]
            _level: str = "level1"
            mode: ClassVar[str] = "m1"

            @command()
            def action(self) -> str:
                return "level1"

            def describe(self) -> str:
                return "d1"

        class Level2(Level1):
            level2_field: str = "level2"
            _level: str = "level2"

        class Level3(Level2):
            level3_field: str = "level3"
            _level: str = "level3"
            mode: ClassVar[str] = "m3"

            @command()
            def action(self) -> str:
                return "level3"

            def describe(self) -> str:
                return "d3"

        class SkipLevel2(Level3, Level1):
            pass

        bakebook = SkipLevel2()

        # Native mirror of the same shape resolves via the MRO.
        class NativeLevel1:
            level1_field = "level1"
            serial: ClassVar[list[str]] = ["s1"]
            _level = "level1"
            mode = "m1"

            def action(self) -> str:
                return "level1"

            def describe(self) -> str:
                return "d1"

        class NativeLevel2(NativeLevel1):
            level2_field = "level2"
            _level = "level2"

        class NativeLevel3(NativeLevel2):
            level3_field = "level3"
            _level = "level3"
            mode = "m3"

            def action(self) -> str:
                return "level3"

            def describe(self) -> str:
                return "d3"

        class NativeSkip(NativeLevel3, NativeLevel1):
            pass

        native = NativeSkip()
        assert bakebook.level1_field == native.level1_field == "level1"
        assert bakebook.serial == native.serial == ["s1"]
        assert bakebook.level2_field == native.level2_field == "level2"
        assert bakebook.level3_field == native.level3_field == "level3"
        assert bakebook._level == native._level == "level3"
        assert bakebook.mode == native.mode == "m3"
        assert bakebook.action() == native.action() == "level3"
        assert bakebook.describe() == native.describe() == "d3"
        assert SkipLevel2.model_config["env_file"] == ".sl1"

    def test_concrete_implementations(self) -> None:
        # Two concretes of one abstract, each composed with a second abstract.
        class AbstractBakebook1(Bakebook):
            model_config = SettingsConfigDict(env_file=".abs1")

            field1: str = "value1"
            _knob: str = "abs1"
            mode: ClassVar[str] = "abs-mode"

            @command()
            def action1(self) -> str:
                return f"action1: {self.field1}"

            def greet(self) -> str:
                return "abs-greet"

        class ConcreteBakebook1A(AbstractBakebook1):
            field1: str = "concrete1a"
            _knob: str = "c1a"
            mode: ClassVar[str] = "c1a-mode"

            @command()
            def action1(self) -> str:
                return f"concrete1a: {self.field1}"

        class ConcreteBakebook1B(AbstractBakebook1):
            field1: str = "concrete1b"
            _knob: str = "c1b"
            mode: ClassVar[str] = "c1b-mode"

            def action1(self) -> str:
                return f"concrete1b override: {self.field1}"

        class AbstractBakebook2(Bakebook):
            field2: str = "value2"
            parts: Annotated[list[str], Field(default_factory=lambda: ["abs2"])]

            @command()
            def action2(self) -> str:
                return f"action2: {self.field2}"

        class BakebookWith1A(ConcreteBakebook1A, AbstractBakebook2):
            pass

        class BakebookWith1B(ConcreteBakebook1B, AbstractBakebook2):
            pass

        bakebook_a = BakebookWith1A()
        bakebook_b = BakebookWith1B()

        # Native mirror of the field/private/ClassVar resolution (commands are
        # typer machinery).
        class NativeAbs1:
            field1 = "value1"
            _knob = "abs1"
            mode = "abs-mode"

            def greet(self) -> str:
                return "abs-greet"

        class Native1A(NativeAbs1):
            field1 = "concrete1a"
            _knob = "c1a"
            mode = "c1a-mode"

        class Native1B(NativeAbs1):
            field1 = "concrete1b"
            _knob = "c1b"
            mode = "c1b-mode"

        class NativeAbs2:
            field2 = "value2"
            parts: ClassVar[list[str]] = ["abs2"]

        class NativeA(Native1A, NativeAbs2):
            pass

        class NativeB(Native1B, NativeAbs2):
            pass

        assert bakebook_a.field1 == NativeA().field1 == "concrete1a"
        assert bakebook_b.field1 == NativeB().field1 == "concrete1b"
        assert bakebook_a.field2 == "value2"
        assert bakebook_b.field2 == "value2"
        assert bakebook_a.parts == NativeA().parts == ["abs2"]
        assert bakebook_b.parts == NativeB().parts == ["abs2"]
        assert bakebook_a._knob == NativeA()._knob == "c1a"
        assert bakebook_b._knob == NativeB()._knob == "c1b"
        assert bakebook_a.mode == NativeA.mode == "c1a-mode"
        assert bakebook_b.mode == NativeB.mode == "c1b-mode"
        assert bakebook_a.greet() == NativeA().greet() == "abs-greet"
        assert BakebookWith1A.model_config["env_file"] == ".abs1"
        assert BakebookWith1B.model_config["env_file"] == ".abs1"

        @bakebook_a.command()
        @bakebook_b.command()
        def some_action():
            return "some_action"

        assert_commands(
            bakebook=bakebook_a,
            expected_commands={
                "action1": ExpectedCommand(
                    name="action1", command_type=types.MethodType, output="concrete1a: concrete1a"
                ),
                "action2": ExpectedCommand(
                    name="action2", command_type=types.MethodType, output="action2: value2"
                ),
                "some_action": ExpectedCommand(
                    name="some_action", command_type=types.FunctionType, output="some_action"
                ),
            },
            msg="BakebookWith1A",
        )

        assert_commands(
            bakebook=bakebook_b,
            expected_commands={
                "action1": ExpectedCommand(
                    name="action1",
                    command_type=types.MethodType,
                    output="concrete1b override: concrete1b",
                ),
                "action2": ExpectedCommand(
                    name="action2", command_type=types.MethodType, output="action2: value2"
                ),
                "some_action": ExpectedCommand(
                    name="some_action", command_type=types.FunctionType, output="some_action"
                ),
            },
            msg="BakebookWith1B",
        )

    def test_cooperative_super_follows_mro(self) -> None:
        # Cooperative dispatch: each base layers onto the next via super(), and
        # the MRO alone decides the order the layers run in. Every other kind
        # rides the same graph.
        class SpaceBase(Bakebook):
            model_config = SettingsConfigDict(env_file=".base")

            shared: str = "base"
            tags: Annotated[list[str], Field(default_factory=lambda: ["base"])]
            _shared: str = "base"
            mode: ClassVar[str] = "base-mode"

            @command()
            def run(self) -> str:
                return "base-run"

            def pipeline(self) -> list[str]:
                return ["base"]

        class LeftSpace(SpaceBase):
            model_config = SettingsConfigDict(env_file=".left")

            tag: str = "left"
            _tag: str = "left"
            mode: ClassVar[str] = "left-mode"

            @command()
            def run(self) -> str:
                return "left-run"

            def pipeline(self) -> list[str]:
                return ["left", *super().pipeline()]

        class RightSpace(SpaceBase):
            model_config = SettingsConfigDict(env_file=".right")

            tag: str = "right"
            _tag: str = "right"
            mode: ClassVar[str] = "right-mode"

            @command()
            def run(self) -> str:
                return "right-run"

            def pipeline(self) -> list[str]:
                return ["right", *super().pipeline()]

        class Composed(LeftSpace, RightSpace):
            pass

        class Swapped(RightSpace, LeftSpace):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            shared = "base"
            tags: ClassVar[list[str]] = ["base"]
            _shared = "base"
            mode = "base-mode"

            def run(self) -> str:
                return "base-run"

            def pipeline(self) -> list[str]:
                return ["base"]

        class NativeLeft(NativeBase):
            tag = "left"
            _tag = "left"
            mode = "left-mode"

            def run(self) -> str:
                return "left-run"

            def pipeline(self) -> list[str]:
                return ["left", *super().pipeline()]

        class NativeRight(NativeBase):
            tag = "right"
            _tag = "right"
            mode = "right-mode"

            def run(self) -> str:
                return "right-run"

            def pipeline(self) -> list[str]:
                return ["right", *super().pipeline()]

        class NativeComposed(NativeLeft, NativeRight):
            pass

        class NativeSwapped(NativeRight, NativeLeft):
            pass

        for bakebook, native, env in (
            (Composed(), NativeComposed(), ".left"),
            (Swapped(), NativeSwapped(), ".right"),
        ):
            label = type(bakebook).__name__
            assert bakebook.shared == native.shared == "base", label
            assert bakebook.tags == native.tags == ["base"], label
            assert bakebook.tag == native.tag, label
            assert bakebook._shared == native._shared == "base", label
            assert bakebook._tag == native._tag, label
            assert bakebook.mode == native.mode, label
            assert bakebook.run() == native.run(), label
            assert bakebook.pipeline() == native.pipeline(), label
            assert type(bakebook).model_config["env_file"] == env, label

            assert_commands(
                bakebook,
                {
                    "run": ExpectedCommand(
                        name="run", command_type=types.MethodType, output=native.run()
                    ),
                },
                msg=f"{label}: command follows MRO",
            )

        assert Composed().tag == NativeComposed().tag == "left"
        assert Composed().mode == NativeComposed().mode == "left-mode"
        assert Composed().pipeline() == NativeComposed().pipeline() == ["left", "right", "base"]
        assert Swapped().tag == NativeSwapped().tag == "right"
        assert Swapped().mode == NativeSwapped().mode == "right-mode"
        assert Swapped().pipeline() == NativeSwapped().pipeline() == ["right", "left", "base"]

    def test_composed_of_composed_all_kinds_resolves_mro(self) -> None:
        # A fixed compose (Swapped: plain sibling before the override) becomes
        # a base of a second compose — the deepest MRO the declarer walk
        # faces. The inner fix must survive being flattened again.
        class SpaceBase(Bakebook):
            model_config = SettingsConfigDict(env_file=".cc-base")

            knob: str = "base"
            _knob: str = "base-default"
            mode: ClassVar[str] = "base-mode"

            @command()
            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

        class OverrideSpace(SpaceBase):
            model_config = SettingsConfigDict(env_file=".cc-override")

            knob: str = "override"
            _knob: str = "override"
            mode: ClassVar[str] = "override-mode"

            @command()
            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

        class PlainSpace(SpaceBase):
            pass

        class Swapped(PlainSpace, OverrideSpace):
            pass

        class OtherSpace(Bakebook):
            model_config = SettingsConfigDict(case_sensitive=True)

            other: Annotated[list[str], Field(default_factory=lambda: ["other"])]
            _other: str = "other-secret"
            other_mode: ClassVar[str] = "other-mode"

            @command()
            def other_cmd(self) -> str:
                return "other-cmd"

            def other_method(self) -> str:
                return "other-method"

        class DeepA(Swapped, OtherSpace):
            pass

        class DeepB(OtherSpace, Swapped):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            knob = "base"
            _knob = "base-default"
            mode = "base-mode"

            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

        class NativeOverride(NativeBase):
            knob = "override"
            _knob = "override"
            mode = "override-mode"

            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

        class NativePlain(NativeBase):
            pass

        class NativeSwapped(NativePlain, NativeOverride):
            pass

        class NativeOther:
            other: ClassVar[list[str]] = ["other"]
            _other = "other-secret"
            other_mode = "other-mode"

            def other_cmd(self) -> str:
                return "other-cmd"

            def other_method(self) -> str:
                return "other-method"

        class NativeDeepA(NativeSwapped, NativeOther):
            pass

        class NativeDeepB(NativeOther, NativeSwapped):
            pass

        # The kwargs path (pydantic-specific) still initializes both graphs.
        assert DeepA(other=["from-kwargs"]).other == ["from-kwargs"]
        assert DeepB(knob="from-kwargs").knob == "from-kwargs"

        for bakebook, native in ((DeepA(), NativeDeepA()), (DeepB(), NativeDeepB())):
            label = type(bakebook).__name__
            assert bakebook.knob == native.knob == "override", label
            assert bakebook._knob == native._knob == "override", label
            assert bakebook.mode == native.mode == "override-mode", label
            assert bakebook.method() == native.method() == "override-method", label
            assert bakebook.other == native.other == ["other"], label
            assert bakebook._other == native._other == "other-secret", label
            assert bakebook.other_mode == native.other_mode == "other-mode", label
            assert bakebook.other_method() == native.other_method() == "other-method", label
            # The inner fix survives the outer compose; the disjoint outer
            # key survives the fold.
            assert type(bakebook).model_config["env_file"] == ".cc-override", label
            assert type(bakebook).model_config["case_sensitive"] is True, label

            assert_commands(
                bakebook,
                {
                    "cmd": ExpectedCommand(
                        name="cmd", command_type=types.MethodType, output="override-cmd"
                    ),
                    "other_cmd": ExpectedCommand(
                        name="other_cmd",
                        command_type=types.MethodType,
                        output="other-cmd",
                    ),
                },
                msg=f"{label}: both graphs' commands register",
            )


class TestRedeclaration:
    """
    Redeclaration: the composed class redeclares, or a further subclass
    inherits the fixed snapshot.
    """

    def test_own_redeclaration_wins(self) -> None:
        # The composed class's own body wins over every branch, every kind —
        # including a fresh PrivateAttr factory and an own model_config key.
        class MatrixBase(Bakebook):
            model_config = SettingsConfigDict(env_file=".own-base")

            plain_field: str = "base-field"
            factory_field: Annotated[str, Field(default_factory=lambda: "base-factory")]
            class_var: ClassVar[str] = "base-classvar"
            _knob: str = PrivateAttr(default_factory=lambda: "base-factory")

            @command()
            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

        class MatrixOverride(MatrixBase):
            model_config = SettingsConfigDict(env_file=".own-override")

            plain_field: str = "override-field"
            factory_field: Annotated[str, Field(default_factory=lambda: "override-factory")]
            class_var: ClassVar[str] = "override-classvar"
            _knob: str = PrivateAttr(default_factory=lambda: "override-factory")

            @command()
            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

        class MatrixPlain(MatrixBase):
            pass

        class Redeclared(MatrixPlain, MatrixOverride):
            model_config = SettingsConfigDict(env_file=".own")

            plain_field: str = "own-field"
            factory_field: Annotated[str, Field(default_factory=lambda: "own-factory")]
            class_var: ClassVar[str] = "own-var"
            _knob = PrivateAttr(default_factory=lambda: "own-factory")

            @command()
            def cmd(self) -> str:
                return "own-cmd"

            def method(self) -> str:
                return "own-method"

        # Native mirror of the same shape resolves via the MRO. The factory's
        # product stands in as a plain default.
        class NativeBase:
            plain_field = "base-field"
            factory_field = "base-factory"
            class_var = "base-classvar"
            _knob = "base-factory"

            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

        class NativeOverride(NativeBase):
            plain_field = "override-field"
            factory_field = "override-factory"
            class_var = "override-classvar"
            _knob = "override-factory"

            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

        class NativePlain(NativeBase):
            pass

        class NativeRedeclared(NativePlain, NativeOverride):
            plain_field = "own-field"
            factory_field = "own-factory"
            class_var = "own-var"
            _knob = "own-factory"

            def cmd(self) -> str:
                return "own-cmd"

            def method(self) -> str:
                return "own-method"

        bakebook = Redeclared()
        assert bakebook.plain_field == NativeRedeclared().plain_field == "own-field"
        assert bakebook.factory_field == NativeRedeclared().factory_field == "own-factory"
        assert bakebook.class_var == NativeRedeclared().class_var == "own-var"
        assert bakebook._knob == NativeRedeclared()._knob == "own-factory"
        assert bakebook.cmd() == NativeRedeclared().cmd() == "own-cmd"
        assert bakebook.method() == NativeRedeclared().method() == "own-method"
        assert Redeclared.model_config["env_file"] == ".own"

        assert_commands(
            bakebook,
            {
                "cmd": ExpectedCommand(name="cmd", command_type=types.MethodType, output="own-cmd"),
            },
            msg="Own redeclaration replaces the branch registration",
        )

        # The kwargs path (pydantic-specific) still initializes the own field.
        assert Redeclared(plain_field="from-kwargs").plain_field == "from-kwargs"

    def test_fix_survives_further_subclassing(self) -> None:
        # The swapped FieldInfo flattens into the snapshot subclasses inherit;
        # every other fixed kind survives too.
        class SpaceBase(Bakebook):
            model_config = SettingsConfigDict(env_file=".fs-base")

            knob: str = "base"
            serial: Annotated[list[str], Field(default_factory=lambda: ["base-serial"])]
            _knob: str = "base-default"
            mode: ClassVar[str] = "base-mode"

            @command()
            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

        class OverrideSpace(SpaceBase):
            model_config = SettingsConfigDict(env_file=".fs-override")

            knob: str = "override"
            serial: Annotated[list[str], Field(default_factory=lambda: ["override-serial"])]
            _knob: str = "override"
            mode: ClassVar[str] = "override-mode"

            @command()
            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

        class PlainSpace(SpaceBase):
            pass

        class Swapped(PlainSpace, OverrideSpace):
            pass

        class Further(Swapped):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            knob = "base"
            serial: ClassVar[list[str]] = ["base-serial"]
            _knob = "base-default"
            mode = "base-mode"

            def cmd(self) -> str:
                return "base-cmd"

            def method(self) -> str:
                return "base-method"

        class NativeOverride(NativeBase):
            knob = "override"
            serial: ClassVar[list[str]] = ["override-serial"]
            _knob = "override"
            mode = "override-mode"

            def cmd(self) -> str:
                return "override-cmd"

            def method(self) -> str:
                return "override-method"

        class NativePlain(NativeBase):
            pass

        class NativeSwapped(NativePlain, NativeOverride):
            pass

        class NativeFurther(NativeSwapped):
            pass

        bakebook = Further()
        assert bakebook.knob == NativeFurther().knob == "override"
        assert bakebook.serial == NativeFurther().serial == ["override-serial"]
        assert bakebook._knob == NativeFurther()._knob == "override"
        assert bakebook.mode == NativeFurther().mode == "override-mode"
        assert bakebook.cmd() == NativeFurther().cmd() == "override-cmd"
        assert bakebook.method() == NativeFurther().method() == "override-method"
        assert Further.model_config["env_file"] == ".fs-override"
        assert Further.__pydantic_fields__["knob"].default == "override"

        assert_commands(
            bakebook,
            {
                "cmd": ExpectedCommand(
                    name="cmd", command_type=types.MethodType, output="override-cmd"
                ),
            },
            msg="Further subclass keeps the fixed registration",
        )


class TestKindFlips:
    """
    Kind flips: a name changes kind between declarers — ClassVar vs field,
    defaulted vs required, one annotation vs another. The flip is the
    pattern, so these graphs stay focused on the flipped name.
    """

    def test_classvar_vs_field_both_orders(self) -> None:
        # get_annotations lists ClassVar names too, so the declarer walk sees
        # both kinds: the MRO-first declarer decides which kind the name is.
        class VarFirst(Bakebook):
            knob: ClassVar[str] = "var"

        class FieldLater(Bakebook):
            knob: str = "field"

        class VarWins(VarFirst, FieldLater):
            pass

        class FieldWins(FieldLater, VarFirst):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeVarFirst:
            knob = "var"

        class NativeFieldLater:
            knob = "field"

        class NativeVarWins(NativeVarFirst, NativeFieldLater):
            pass

        class NativeFieldWins(NativeFieldLater, NativeVarFirst):
            pass

        assert VarWins.knob == NativeVarWins.knob == "var"
        # pydantic drops the field entirely under a MRO-first ClassVar declarer.
        assert "knob" not in VarWins.__pydantic_fields__

        assert FieldWins().knob == NativeFieldWins().knob == "field"
        assert FieldWins(knob="from-kwargs").knob == "from-kwargs"
        assert "knob" in FieldWins.__pydantic_fields__

    def test_field_to_classvar_redeclare_down_chain(self) -> None:
        class SpaceBase(Bakebook):
            knob: str = "field"

        class VarChild(SpaceBase):
            knob: ClassVar[str] = "var"  # ty: ignore[invalid-attribute-override]

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            knob = "field"

        class NativeVarChild(NativeBase):
            knob = "var"

        assert VarChild.knob == NativeVarChild.knob == "var"
        assert "knob" not in VarChild.__pydantic_fields__

    def test_required_redeclare_resolves_mro(self) -> None:
        # A bare annotation declares a required field — required-ness has no
        # native counterpart (an annotation alone creates no attribute), so the
        # assert is direct. The declarer still wins the MRO: the sibling's
        # inherited defaulted copy must not shadow it.
        class SpaceBase(Bakebook):
            knob: str = "base"

        class RequiredSpace(SpaceBase):
            knob: str

        class PlainSpace(SpaceBase):
            pass

        class Composed(RequiredSpace, PlainSpace):
            pass

        class Swapped(PlainSpace, RequiredSpace):
            pass

        assert RequiredSpace.__pydantic_fields__["knob"].is_required()
        assert Composed.__pydantic_fields__["knob"].is_required()
        assert Swapped.__pydantic_fields__["knob"].is_required()
        assert Swapped(knob="from-kwargs").knob == "from-kwargs"
        with pytest.raises(ValidationError):
            Swapped()

    def test_type_change_override_follows_mro(self) -> None:
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class TypedSpace(SpaceBase):
            knob: int = 7
            _knob: int = 7

        class PlainSpace(SpaceBase):
            pass

        class Composed(TypedSpace, PlainSpace):
            pass

        class Swapped(PlainSpace, TypedSpace):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            knob = "base"
            _knob = "base-default"

        class NativeTyped(NativeBase):
            knob = 7
            _knob = 7

        class NativePlain(NativeBase):
            pass

        class NativeComposed(NativeTyped, NativePlain):
            pass

        class NativeSwapped(NativePlain, NativeTyped):
            pass

        assert Composed().knob == NativeComposed().knob == 7
        assert Composed()._knob == NativeComposed()._knob == 7
        assert Swapped().knob == NativeSwapped().knob == 7
        assert Swapped()._knob == NativeSwapped()._knob == 7
        assert Composed.__pydantic_fields__["knob"].annotation is int
        assert Swapped.__pydantic_fields__["knob"].annotation is int

    def test_method_to_command_flip_follows_mro(self) -> None:
        # The parent's plain method, the child's @command: the flip registers
        # the name once and the MRO still decides the callable, in either
        # base order (the plain sibling never declares it).
        class SpaceBase(Bakebook):
            def action(self) -> str:
                return "plain-base"

        class CommandSpace(SpaceBase):
            @command()
            def action(self) -> str:
                return "command-space"

        class PlainSpace(SpaceBase):
            pass

        class Composed(CommandSpace, PlainSpace):
            pass

        class Swapped(PlainSpace, CommandSpace):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            def action(self) -> str:
                return "plain-base"

        class NativeCommand(NativeBase):
            def action(self) -> str:
                return "command-space"

        class NativePlain(NativeBase):
            pass

        class NativeComposed(NativeCommand, NativePlain):
            pass

        class NativeSwapped(NativePlain, NativeCommand):
            pass

        for bakebook, native in ((Composed(), NativeComposed()), (Swapped(), NativeSwapped())):
            label = type(bakebook).__name__
            assert bakebook.action() == native.action() == "command-space", label

            assert_commands(
                bakebook,
                {
                    "action": ExpectedCommand(
                        name="action",
                        command_type=types.MethodType,
                        output="command-space",
                    ),
                },
                msg=f"{label}: flip registers the name exactly once",
            )
            assert len(bakebook._app.registered_commands) == 1, label

    def test_private_attr_required_redeclare_resolves_mro(self) -> None:
        # A bare private-attr annotation redeclares the parent's defaulted one
        # as required: the remerge keeps it default-less, access raises until
        # set, and the sibling's inherited defaulted copy never shadows it.
        class SpaceBase(Bakebook):
            _knob: str = "base-default"

        class RequiredSpace(SpaceBase):
            _knob: str

        class PlainSpace(SpaceBase):
            pass

        class Composed(RequiredSpace, PlainSpace):
            pass

        class Swapped(PlainSpace, RequiredSpace):
            pass

        # Native mirror: a bare annotation assigns nothing, so the parent's
        # default stays visible — required-ness has no native counterpart.
        class NativeBase:
            _knob = "base-default"

        class NativeRequired(NativeBase):
            _knob: str

        class NativePlain(NativeBase):
            pass

        class NativeComposed(NativeRequired, NativePlain):
            pass

        class NativeSwapped(NativePlain, NativeRequired):
            pass

        assert SpaceBase()._knob == "base-default"
        assert "_knob" in Composed.__private_attributes__
        assert "_knob" in Swapped.__private_attributes__
        for model, native in ((Composed, NativeComposed), (Swapped, NativeSwapped)):
            label = model.__name__
            # pydantic treats the bare annotation as a declaration (required,
            # no default); a plain-Python annotation assigns nothing, so the
            # mirror's parent default stays visible — assert pydantic directly.
            with pytest.raises(AttributeError):
                _ = model()._knob
            assert native()._knob == "base-default", label
            bakebook = model()
            bakebook._knob = "per-instance"
            assert bakebook._knob == "per-instance", label


class TestGenerics:
    """
    Generics: parametrized aliases substitute typevars through machinery
    the declarer walk cannot see, so alias claims are asserted directly.
    The alias hazard is field-specific; all-kind asserts here would be
    vacuous, so these pins stay field-focused.
    """

    def test_parametrized_alias_creation_no_raise(self) -> None:
        class GenericKnobSpace(Bakebook, Generic[E]):
            knob: E

        aliased = GenericKnobSpace[str]

        assert aliased.__pydantic_fields__["knob"].annotation is str

    def test_parametrized_generic_base_no_raise(self) -> None:
        # Parametrized generic bases fill fields via generic machinery, not
        # class-body annotations; pydantic resolves the substituted copy correctly.
        class GenericKnobSpace(Bakebook, Generic[E]):
            knob: E
            _knob: str = "generic"

        class OtherSpace(Bakebook):
            other: str = "other"

        class Composed(OtherSpace, GenericKnobSpace[str]):
            pass

        bakebook = Composed(knob="from-kwargs")
        assert Composed.__pydantic_fields__["knob"].annotation is str
        assert bakebook.knob == "from-kwargs"
        assert bakebook._knob == "generic"

    def test_parametrized_generic_three_bases_no_raise(self) -> None:
        # data-kit GLZServiceSpace shape: 'knob' lives only on the generic branch.
        class GenericKnobSpace(Bakebook, Generic[E]):
            knob: E

        class ToolsSpace(Bakebook):
            tool: str = "tool"

        class ServiceSpace(Bakebook):
            service: str = "service"

        class Composed(ToolsSpace, GenericKnobSpace[str], ServiceSpace):
            pass

        assert Composed.__pydantic_fields__["knob"].annotation is str
        assert Composed(knob="from-kwargs").knob == "from-kwargs"

    def test_generic_alias_first_wins_no_raise(self) -> None:
        class SpaceBase(Bakebook):
            knob: str = "base"

        class GenericOverrideSpace(SpaceBase, Generic[E]):
            knob: E

        class PlainSpace(SpaceBase):
            pass

        class Composed(GenericOverrideSpace[str], PlainSpace):
            pass

        # The generic branch's required knob wins — not SpaceBase's defaulted one.
        assert Composed.__pydantic_fields__["knob"].is_required()
        assert Composed(knob="override").knob == "override"

    def test_generic_branch_bug_shape_resolves_mro(self) -> None:
        # The plain sibling's inherited snapshot no longer beats the alias's
        # substituted override.
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class GenericOverrideSpace(SpaceBase, Generic[E]):
            knob: E
            _knob: str = "override"

        class PlainSpace(SpaceBase):
            pass

        class Swapped(PlainSpace, GenericOverrideSpace[str]):
            pass

        bakebook = Swapped(knob="override")
        assert Swapped.__pydantic_fields__["knob"].is_required()
        assert bakebook.knob == "override"
        assert bakebook._knob == "override"

    def test_generic_alias_does_not_claim_inherited_field(self) -> None:
        # The alias claims only names its chain re-declares; inherited 'knob'
        # stays with declarer SpaceBase and raises nothing.
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class GenericSiblingSpace(SpaceBase, Generic[E]):
            other: E

        class PlainSpace(SpaceBase):
            pass

        class Composed(PlainSpace, GenericSiblingSpace[str]):
            pass

        bakebook = Composed(other="sibling")
        assert bakebook.knob == "base"
        assert bakebook.other == "sibling"
        assert bakebook._knob == "base-default"

    def test_generic_subclass_alias_no_raise(self) -> None:
        # Substitution flows through the whole chain even without redeclaration,
        # so the alias's copy is the correct resolution.
        class GenericKnobSpace(Bakebook, Generic[E]):
            knob: E

        class SubSpace(GenericKnobSpace[E]):
            extra: str = "extra"

        class OtherSpace(Bakebook):
            other: str = "other"

        class Composed(OtherSpace, SubSpace[str]):
            pass

        assert Composed.__pydantic_fields__["knob"].annotation is str
        bakebook = Composed(knob="from-kwargs")
        assert bakebook.knob == "from-kwargs"
        assert bakebook.extra == "extra"

    def test_generic_subclass_alias_bug_shape_resolves_mro(self) -> None:
        # Resolution survives subclass aliases: inherited snapshot no longer
        # shadows the substituted override.
        class SpaceBase(Bakebook):
            knob: str = "base"

        class GenericOverrideSpace(SpaceBase, Generic[E]):
            knob: E

        class SubOverrideSpace(GenericOverrideSpace[E]):
            extra: str = "extra"

        class PlainSpace(SpaceBase):
            pass

        class Swapped(PlainSpace, SubOverrideSpace[str]):
            pass

        assert Swapped.__pydantic_fields__["knob"].is_required()
        bakebook = Swapped(knob="override")
        assert bakebook.knob == "override"
        assert bakebook.extra == "extra"

    def test_alias_does_not_claim_parallel_branch_field(self) -> None:
        # 'knob' comes from a parallel branch, so the alias does not claim it —
        # its inherited snapshot no longer shadows the override.
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class GenericSiblingSpace(SpaceBase, Generic[E]):
            other: E

        class OverrideSpace(SpaceBase):
            knob: str = "override"
            _knob: str = "override"

        class Swapped(GenericSiblingSpace[str], OverrideSpace):
            pass

        # Native mirror of the knob resolution ('other' is generic machinery).
        class NativeBase:
            knob = "base"
            _knob = "base-default"

        class NativeSibling(NativeBase):
            pass

        class NativeOverride(NativeBase):
            knob = "override"
            _knob = "override"

        class NativeSwapped(NativeSibling, NativeOverride):
            pass

        bakebook = Swapped(other="sibling")
        assert bakebook.knob == NativeSwapped().knob == "override"
        assert bakebook._knob == NativeSwapped()._knob == "override"
        assert bakebook.other == "sibling"

    def test_two_aliases_first_claim_wins(self) -> None:
        class GenericKnobSpace(Bakebook, Generic[E]):
            knob: E

        class BranchASpace(GenericKnobSpace[E]):
            pass

        class BranchBSpace(GenericKnobSpace[E]):
            pass

        class Composed(BranchASpace[str], BranchBSpace[str]):
            pass

        # The first alias's claim stands; the second does not re-claim.
        assert Composed.__pydantic_fields__["knob"].annotation is str

    def test_alias_with_classvar_declarer_no_raise(self) -> None:
        # ClassVar declarers have no field entry: the claim loop skips them, and
        # the expected_field-is-None path applies.
        class VarFirst(Bakebook):
            knob: ClassVar[str] = "var"

        class FieldLater(Bakebook):
            knob: str = "field"

        class GenericMiddle(FieldLater, Generic[E]):
            other: E

        class Composed(VarFirst, GenericMiddle[str]):
            pass

        assert Composed.knob == "var"
        assert Composed(knob="from-kwargs", other="from-kwargs").other == "from-kwargs"


class TestNonPatternEdges:
    """
    Non-pattern edges: behaviors that are not inheritance patterns (instance
    assignment shadowing, remerge guard rails) stay in their own small tests.
    """

    def test_private_attr_instance_assignment_still_wins(self) -> None:
        """Per-instance values keep working — the knob stays a private attr."""

        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class OverrideSpace(SpaceBase):
            knob: str = "override"
            _knob: str = "override"

        class PlainSpace(SpaceBase):
            pass

        class Composed(OverrideSpace, PlainSpace):
            pass

        bakebook = Composed()
        bakebook._knob = "per-instance"
        bakebook.knob = "per-instance-field"
        assert bakebook._knob == "per-instance"
        assert bakebook.knob == "per-instance-field"
        assert Composed()._knob == "override"
        assert Composed().knob == "override"

    def test_remerge_skips_class_without_private_attributes(self) -> None:
        class NoSnapshotModel(BaseModel):
            _knob: str = "own"

        del NoSnapshotModel.__private_attributes__

        _remerge_private_attributes_mro(NoSnapshotModel)

        assert "__private_attributes__" not in NoSnapshotModel.__dict__

    def test_remerge_skips_single_pydantic_base(self) -> None:
        class DirectModel(BaseModel):
            _knob: str = "own"

        snapshot = DirectModel.__dict__["__private_attributes__"]

        _remerge_private_attributes_mro(DirectModel)

        assert DirectModel.__dict__["__private_attributes__"] is snapshot

    def test_fix_field_merge_mro_idempotent(self) -> None:
        # pydantic hands every subclass a fresh FieldInfo copy, so the
        # declarer's object only lands in cls.__pydantic_fields__ once the
        # first pass assigns it. A second pass then hits the
        # already-correct path (identity) for every name and must change
        # nothing — no swap, no rebuild.
        class SpaceBase(Bakebook):
            knob: str = "base"

        class OverrideSpace(SpaceBase):
            knob: str = "override"

        class PlainSpace(SpaceBase):
            pass

        class Composed(OverrideSpace, PlainSpace):
            pass

        assert Composed.__pydantic_fields__["knob"] is OverrideSpace.__pydantic_fields__["knob"]

        before = dict(Composed.__pydantic_fields__)
        _fix_field_merge_mro(Composed)
        assert Composed.__pydantic_fields__ == before
        assert Composed.__pydantic_fields__["knob"] is before["knob"]

        bakebook = Composed()
        assert bakebook.knob == "override"
