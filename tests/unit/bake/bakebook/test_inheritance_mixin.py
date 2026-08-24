"""BakebookMixin composition must resolve exactly like native Python.

BakebookMixin subclasses are field/config bundles composed onto Bakebook
subclasses (recommended: attributes only, composed before the bakebook —
see BakebookMixin's docstring in bake/bakebook/bakebook.py). This file
holds the inheritance shapes that mix mixins with bakebooks; the same
native-parity oracle as test_inheritance.py applies: each test builds a
plain-class mirror of the same inheritance graph and asserts the
bakebook and the mirror agree, value for value, in both base orders.

One test func = one composition pattern, and its graph carries every
attribute kind (field, factory field, private attr, ClassVar, method,
@command, model_config key), so the coverage matrix (pattern by kind) is
structural. Tests group into one test class per pattern family — mixin
before the spaces, mixin between them, mixin after them, multiple mixins,
inheritance within mixins, layered composition, redeclaration, kind flips
between mixin and book, generic mixins — and each class docstring
explains its family. Two families stay
kind-narrow by design: kind flips (the flip is the pattern) and generic
mixins (machinery pins — the alias hazard is field-specific, so all-kind
asserts there would be vacuous).
"""

import types
from typing import Annotated, ClassVar, Generic, TypeVar

import pytest
from pydantic import Field, PrivateAttr
from pydantic_settings import SettingsConfigDict

from bake import Bakebook, BakebookMixin, command
from tests.unit.bake.bakebook.utils import ExpectedCommand, assert_commands

E = TypeVar("E")


class TestMixinBeforeSpaces:
    """
    Mixin before the spaces (the recommended order): the mixin wins every
    conflicting kind, its sole-declared kinds ride along, and the book's
    methods consume them.
    """

    def test_mixin_first_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The recommended shape: mixin composed before the spaces wins every
        # kind it declares, in either space order — including the plain-first
        # bug shape. The mixin's model_config key wins too, keys only the
        # book chain declares still resolve, and the re-resolved prefix is
        # what settings sources read at init (runtime assert).
        class SpaceBase(Bakebook):
            knob: str = "base"
            serial: str = "book-only"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class OverrideSpace(SpaceBase):
            knob: str = "override"
            _knob: str = "override"
            mode: ClassVar[str] = "override-var"

            def describe(self) -> str:
                return "override"

        class PlainSpace(SpaceBase):
            pass

        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_prefix="mix_")

            knob: str = "mixin"
            tags: Annotated[list[str], Field(default_factory=lambda: ["mix"])]
            _knob: str = "mixin"
            _factory: str = PrivateAttr(default_factory=lambda: "mix-factory")
            mode: ClassVar[str] = "mixin-var"

            @command()
            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class Composed(KnobMixin, OverrideSpace, PlainSpace):
            pass

        class Swapped(KnobMixin, PlainSpace, OverrideSpace):
            pass

        # Native mirror of the same shape resolves via the MRO. Config mirrors
        # at key level (env_prefix from the mixin's dict).
        class NativeBase:
            knob = "base"
            serial = "book-only"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeOverride(NativeBase):
            knob = "override"
            _knob = "override"
            mode = "override-var"

            def describe(self) -> str:
                return "override"

        class NativePlain(NativeBase):
            pass

        class NativeMixin:
            knob = "mixin"
            tags: ClassVar[list[str]] = ["mix"]
            _knob = "mixin"
            _factory = "mix-factory"
            mode = "mixin-var"
            model_config: ClassVar[dict[str, str]] = {"env_prefix": "mix_"}

            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class NativeComposed(NativeMixin, NativeOverride, NativePlain):
            pass

        class NativeSwapped(NativeMixin, NativePlain, NativeOverride):
            pass

        for bakebook, native in ((Composed(), NativeComposed()), (Swapped(), NativeSwapped())):
            label = type(bakebook).__name__
            assert bakebook.knob == native.knob == "mixin", label
            assert bakebook.tags == native.tags == ["mix"], label
            assert bakebook._knob == native._knob == "mixin", label
            assert bakebook._factory == native._factory == "mix-factory", label
            assert bakebook.serial == native.serial == "book-only", label
            assert type(bakebook).mode == native.mode == "mixin-var", label
            assert bakebook.describe() == native.describe() == "mixin", label
            assert bakebook.mix_action() == "mixin-action", label
            assert (
                type(bakebook).model_config["env_prefix"]
                == native.model_config["env_prefix"]
                == "mix_"
            ), label

        # Instance assignment beats the mixin's private-attr factory
        # (pydantic surface; the mirror's plain assignment is trivially first).
        instance = Composed()
        instance._factory = "per-instance"
        assert instance._factory == "per-instance"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="mixin-action"
                ),
            },
            msg="Command declared on a mixin registers through the MRO",
        )

        # The kwargs path (pydantic-specific) still initializes the mixin field.
        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Composed.model_config["env_file"] == ".env"

        # Runtime effect: the prefix routes the env var to the mixin's field.
        monkeypatch.setenv("MIX_KNOB", "from-env")
        assert Composed().knob == "from-env"

    def test_mixin_fields_consumed_by_book_methods(self) -> None:
        # The bundle use case: the mixin carries the knobs (including a
        # default_factory field), the book's methods and commands consume them.
        class DockerMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".docker")

            image: str = "python:3.12"
            replicas: Annotated[list[str], Field(default_factory=lambda: ["web", "api"])]
            _registry: str = "internal"
            platform: ClassVar[str] = "linux/amd64"

            @command()
            def push(self) -> str:
                return f"push {self._registry}/{self.image}"

        class DeployBook(Bakebook):
            @command()
            def deploy(self) -> str:
                # Attrs come from the mixin composed below; ty cannot see them.
                return f"{self._registry}/{self.image}"  # ty: ignore[unresolved-attribute]

            def scale(self) -> str:
                # Attrs come from the mixin composed below; ty cannot see them.
                return f"{len(self.replicas)}x {self.platform}"  # ty: ignore[unresolved-attribute]

        class Composed(DockerMixin, DeployBook):
            pass

        # Native mirror of the same shape resolves via the MRO. The factory's
        # product stands in as a plain default.
        class NativeMixin:
            image = "python:3.12"
            replicas: ClassVar[list[str]] = ["web", "api"]
            _registry = "internal"
            platform = "linux/amd64"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".docker"}

            def push(self) -> str:
                return f"push {self._registry}/{self.image}"

        class NativeBook:
            def deploy(self) -> str:
                # Attrs come from the mixin composed below; ty cannot see them.
                return f"{self._registry}/{self.image}"  # ty: ignore[unresolved-attribute]

            def scale(self) -> str:
                # Attrs come from the mixin composed below; ty cannot see them.
                return f"{len(self.replicas)}x {self.platform}"  # ty: ignore[unresolved-attribute]

        class NativeComposed(NativeMixin, NativeBook):
            pass

        bakebook = Composed()
        assert bakebook.deploy() == NativeComposed().deploy() == "internal/python:3.12"
        assert bakebook.scale() == NativeComposed().scale() == "2x linux/amd64"
        assert bakebook.push() == NativeComposed().push() == "push internal/python:3.12"
        assert (
            Composed.model_config["env_file"]
            == NativeComposed.model_config["env_file"]
            == ".docker"
        )

        assert_commands(
            Composed(),
            {
                "deploy": ExpectedCommand(
                    name="deploy", command_type=types.MethodType, output="internal/python:3.12"
                ),
                "push": ExpectedCommand(
                    name="push", command_type=types.MethodType, output="push internal/python:3.12"
                ),
            },
            msg="Book command and mixin command both register",
        )

        # The kwargs path (pydantic-specific) initializes the consumed fields.
        assert Composed(image="alpine").deploy() == "internal/alpine"
        assert Composed(replicas=["solo"]).scale() == "1x linux/amd64"


class TestMixinAfterSpaces:
    """
    Mixin after the spaces: a late MRO slot, natively too — the book's
    declarations win every conflict while the mixin's sole-declared kinds
    still come through.
    """

    def test_mixin_after_overriding_space_resolves_mro(self) -> None:
        # The documented footgun: a mixin listed after the spaces sits late in
        # the MRO natively too, so the overriding space wins every conflicting
        # kind — and Bakebook's own env_file declaration (which also precedes
        # the mixin) wins the config key, natively too.
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class OverrideSpace(SpaceBase):
            knob: str = "override"
            _knob: str = "override"
            mode: ClassVar[str] = "override-var"

            def describe(self) -> str:
                return "override"

        class PlainSpace(SpaceBase):
            pass

        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".myenv")

            knob: str = "mixin"
            tags: Annotated[list[str], Field(default_factory=lambda: ["mix"])]
            _knob: str = "mixin"
            _factory: str = PrivateAttr(default_factory=lambda: "mix-factory")
            mode: ClassVar[str] = "mixin-var"

            @command()
            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class Composed(PlainSpace, OverrideSpace, KnobMixin):
            pass

        # Native mirror: the mixin sits after the base in the MRO natively too.
        # NativeBakebook models Bakebook's own env_file declaration: it
        # precedes a late mixin in the MRO, so it wins the key natively too.
        class NativeBakebook:
            model_config: ClassVar[dict[str, str]] = {"env_file": ".env"}

        class NativeBase(NativeBakebook):
            knob = "base"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeOverride(NativeBase):
            knob = "override"
            _knob = "override"
            mode = "override-var"

            def describe(self) -> str:
                return "override"

        class NativePlain(NativeBase):
            pass

        class NativeMixin:
            knob = "mixin"
            tags: ClassVar[list[str]] = ["mix"]
            _knob = "mixin"
            _factory = "mix-factory"
            mode = "mixin-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".myenv"}

            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class NativeComposed(NativePlain, NativeOverride, NativeMixin):
            pass

        bakebook = Composed()
        assert bakebook.knob == NativeComposed().knob == "override"
        assert bakebook.tags == NativeComposed().tags == ["mix"]
        assert bakebook._knob == NativeComposed()._knob == "override"
        assert bakebook._factory == NativeComposed()._factory == "mix-factory"
        assert Composed.mode == NativeComposed.mode == "override-var"
        assert bakebook.describe() == NativeComposed().describe() == "override"
        assert bakebook.mix_action() == "mixin-action"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="mixin-action"
                ),
            },
            msg="Mixin's own command still registers from a late MRO slot",
        )

        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Composed(tags=["from-kwargs"]).tags == ["from-kwargs"]
        assert (
            Composed.model_config["env_file"] == NativeComposed.model_config["env_file"] == (".env")
        )

    def test_mixin_after_space_matches_mro(self) -> None:
        # Two-base mixin-late is NOT the footgun: SpaceBase precedes the mixin
        # in the MRO natively too, so the book's declarations win every
        # conflict while the mixin's sole-declared kinds still come through.
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class PlainSpace(SpaceBase):
            pass

        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".myenv")

            knob: str = "mixin"
            tags: Annotated[list[str], Field(default_factory=lambda: ["mix"])]
            _knob: str = "mixin"
            _factory: str = PrivateAttr(default_factory=lambda: "mix-factory")
            mode: ClassVar[str] = "mixin-var"

            @command()
            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class Composed(PlainSpace, KnobMixin):
            pass

        # Native mirror of the same shape resolves via the MRO. NativeBakebook
        # models Bakebook's own env_file declaration: it precedes a late mixin
        # in the MRO, so it wins the key natively too.
        class NativeBakebook:
            model_config: ClassVar[dict[str, str]] = {"env_file": ".env"}

        class NativeBase(NativeBakebook):
            knob = "base"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativePlain(NativeBase):
            pass

        class NativeMixin:
            knob = "mixin"
            tags: ClassVar[list[str]] = ["mix"]
            _knob = "mixin"
            _factory = "mix-factory"
            mode = "mixin-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".myenv"}

            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class NativeComposed(NativePlain, NativeMixin):
            pass

        bakebook = Composed()
        assert bakebook.knob == NativeComposed().knob == "base"
        assert bakebook.tags == NativeComposed().tags == ["mix"]
        assert bakebook._knob == NativeComposed()._knob == "base-default"
        assert bakebook._factory == NativeComposed()._factory == "mix-factory"
        assert Composed.mode == NativeComposed.mode == "book-var"
        assert bakebook.describe() == NativeComposed().describe() == "book"
        assert bakebook.mix_action() == "mixin-action"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="mixin-action"
                ),
            },
            msg="Mixin command registers alongside the book's kinds",
        )

        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Composed(tags=["from-kwargs"]).tags == ["from-kwargs"]
        assert (
            Composed.model_config["env_file"] == NativeComposed.model_config["env_file"] == (".env")
        )


class TestMixinBetweenSpaces:
    """
    Mixin between two books: one book branch precedes it in the MRO,
    another follows — the only shape where the mixin both beats a book
    and loses to one.
    """

    def test_mixin_between_spaces_resolves_mro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The sandwich: the preceding book wins every conflicting kind, the
        # mixin beats the following book's declarations, and its sole-declared
        # kinds ride through. In the plain-first swapped order the preceding
        # book only inherits, so the mixin's declarations win — the bug shape
        # with the shadowing snapshot now sitting on the far side of the mixin.
        class SpaceBase(Bakebook):
            knob: str = "base"
            serial: str = "book-only"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class OverrideSpace(SpaceBase):
            knob: str = "override"
            _knob: str = "override"
            mode: ClassVar[str] = "override-var"

            def describe(self) -> str:
                return "override"

        class PlainSpace(SpaceBase):
            pass

        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_prefix="mix_")

            knob: str = "mixin"
            tags: Annotated[list[str], Field(default_factory=lambda: ["mix"])]
            _knob: str = "mixin"
            _factory: str = PrivateAttr(default_factory=lambda: "mix-factory")
            mode: ClassVar[str] = "mixin-var"

            @command()
            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class Composed(OverrideSpace, KnobMixin, PlainSpace):
            pass

        class Swapped(PlainSpace, KnobMixin, OverrideSpace):
            pass

        # Native mirror of the same shape resolves via the MRO — the mixin
        # interleaves between the book branches natively too. Config mirrors
        # at key level (env_prefix from the mixin's dict).
        class NativeBase:
            knob = "base"
            serial = "book-only"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeOverride(NativeBase):
            knob = "override"
            _knob = "override"
            mode = "override-var"

            def describe(self) -> str:
                return "override"

        class NativePlain(NativeBase):
            pass

        class NativeMixin:
            knob = "mixin"
            tags: ClassVar[list[str]] = ["mix"]
            _knob = "mixin"
            _factory = "mix-factory"
            mode = "mixin-var"
            model_config: ClassVar[dict[str, str]] = {"env_prefix": "mix_"}

            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class NativeComposed(NativeOverride, NativeMixin, NativePlain):
            pass

        class NativeSwapped(NativePlain, NativeMixin, NativeOverride):
            pass

        # Composed: the preceding book wins every shared kind.
        bakebook = Composed()
        native = NativeComposed()
        assert bakebook.knob == native.knob == "override"
        assert bakebook._knob == native._knob == "override"
        assert type(bakebook).mode == native.mode == "override-var"
        assert bakebook.describe() == native.describe() == "override"

        # Swapped: the preceding book only inherits, so the mixin's
        # declarations win the shared kinds.
        bakebook = Swapped()
        native = NativeSwapped()
        assert bakebook.knob == native.knob == "mixin"
        assert bakebook._knob == native._knob == "mixin"
        assert type(bakebook).mode == native.mode == "mixin-var"
        assert bakebook.describe() == native.describe() == "mixin"

        # The mixin's sole-declared kinds ride through in both orders.
        for model, native_cls in ((Composed, NativeComposed), (Swapped, NativeSwapped)):
            label = model.__name__
            bakebook = model()
            assert bakebook.tags == native_cls().tags == ["mix"], label
            assert bakebook._factory == native_cls()._factory == "mix-factory", label
            assert bakebook.serial == native_cls().serial == "book-only", label
            assert bakebook.mix_action() == "mixin-action", label
            assert (
                type(bakebook).model_config["env_prefix"]
                == native_cls.model_config["env_prefix"]
                == "mix_"
            ), label

        # Instance assignment beats the mixin's private-attr factory
        # (pydantic surface; the mirror's plain assignment is trivially first).
        instance = Composed()
        instance._factory = "per-instance"
        assert instance._factory == "per-instance"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="mixin-action"
                ),
            },
            msg="Command declared on a mid-MRO mixin registers",
        )

        # The kwargs path (pydantic-specific) still initializes fields.
        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Swapped(tags=["from-kwargs"]).tags == ["from-kwargs"]
        assert Composed.model_config["env_file"] == ".env"

        # Runtime effect: the mixin's prefix routes the env var to a field the
        # preceding book owns — config is class-level, the field's declarer is
        # irrelevant to the env lookup.
        monkeypatch.setenv("MIX_KNOB", "from-env")
        assert Composed().knob == "from-env"
        assert Swapped().knob == "from-env"


class TestMultipleMixins:
    """
    Several mixins against a book, in any base order: the leftmost base
    wins every conflicting kind (factories included), sole-declared kinds
    compose from everyone, and model_config keys resolve per key — disjoint
    keys survive any order, a key shared with Bakebook goes to whichever of
    the two precedes the other in the MRO.
    """

    def test_two_mixins_order_wins(self) -> None:
        # Two mixins: the first wins every conflicting kind. Disjoint
        # model_config keys both survive in either order — each key has a
        # single declarer, so position is irrelevant for those (pydantic#9992's
        # declared-order fold would drop one).
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class FirstMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".first")

            knob: str = "first"
            tags: Annotated[list[str], Field(default_factory=lambda: ["first-tags"])]
            _knob: str = "first"
            mode: ClassVar[str] = "first-mode"

            @command()
            def mix_action(self) -> str:
                return "first-action"

            def describe(self) -> str:
                return "first"

        class SecondMixin(BakebookMixin):
            model_config = SettingsConfigDict(case_sensitive=True)

            knob: str = "second"
            tags: Annotated[list[str], Field(default_factory=lambda: ["second-tags"])]
            _knob: str = "second"
            mode: ClassVar[str] = "second-mode"

            @command()
            def mix_action(self) -> str:
                return "second-action"

            def describe(self) -> str:
                return "second"

        class Composed(FirstMixin, SecondMixin, SpaceBase):
            pass

        class Swapped(SecondMixin, FirstMixin, SpaceBase):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            knob = "base"
            _knob = "base-default"

        class NativeFirst:
            knob = "first"
            tags: ClassVar[list[str]] = ["first-tags"]
            _knob = "first"
            mode = "first-mode"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".first"}

            def mix_action(self) -> str:
                return "first-action"

            def describe(self) -> str:
                return "first"

        class NativeSecond:
            knob = "second"
            tags: ClassVar[list[str]] = ["second-tags"]
            _knob = "second"
            mode = "second-mode"
            model_config: ClassVar[dict[str, object]] = {"case_sensitive": True}

            def mix_action(self) -> str:
                return "second-action"

            def describe(self) -> str:
                return "second"

        # The composed mirrors restate the key-level union: plain attribute
        # lookup would take the first declarer's whole dict, but config
        # resolution is per key.
        class NativeComposed(NativeFirst, NativeSecond, NativeBase):
            model_config: ClassVar[dict[str, object]] = {
                "env_file": ".first",
                "case_sensitive": True,
            }

        class NativeSwapped(NativeSecond, NativeFirst, NativeBase):
            model_config: ClassVar[dict[str, object]] = {
                "env_file": ".first",
                "case_sensitive": True,
            }

        assert Composed().knob == NativeComposed().knob == "first"
        assert Composed().tags == NativeComposed().tags == ["first-tags"]
        assert Composed()._knob == NativeComposed()._knob == "first"
        assert Composed.mode == NativeComposed.mode == "first-mode"
        assert Composed().describe() == NativeComposed().describe() == "first"
        assert Composed().mix_action() == "first-action"

        assert Swapped().knob == NativeSwapped().knob == "second"
        assert Swapped().tags == NativeSwapped().tags == ["second-tags"]
        assert Swapped()._knob == NativeSwapped()._knob == "second"
        assert Swapped.mode == NativeSwapped.mode == "second-mode"
        assert Swapped().describe() == NativeSwapped().describe() == "second"
        assert Swapped().mix_action() == "second-action"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="first-action"
                ),
            },
            msg="First mixin's command wins",
        )
        assert_commands(
            Swapped(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="second-action"
                ),
            },
            msg="Swapped: first-listed mixin's command wins",
        )

        # The kwargs path (pydantic-specific) still initializes the winning
        # mixin's fields.
        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Composed(tags=["from-kwargs"]).tags == ["from-kwargs"]

        # Single declarer per key: order-independent, mirror agrees.
        assert (
            Composed.model_config["env_file"] == NativeComposed.model_config["env_file"] == ".first"
        )
        assert (
            Swapped.model_config["env_file"] == NativeSwapped.model_config["env_file"] == (".first")
        )
        assert (
            Composed.model_config["case_sensitive"]
            is NativeComposed.model_config["case_sensitive"]
            is True
        )
        assert (
            Swapped.model_config["case_sensitive"]
            is NativeSwapped.model_config["case_sensitive"]
            is True
        )

    def test_mixin_vs_declaring_book_order(self) -> None:
        # Direct conflict with no space layer: mixin and book both declare
        # every kind, including the same model_config key. Leftmost wins.
        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".mixin")

            knob: str = "mixin"
            tags: Annotated[list[str], Field(default_factory=lambda: ["mixin-tags"])]
            _knob: str = "mixin"
            mode: ClassVar[str] = "mixin-var"

            @command()
            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class DeclaringBook(Bakebook):
            model_config = SettingsConfigDict(env_file=".book")

            knob: str = "book"
            tags: Annotated[list[str], Field(default_factory=lambda: ["book-tags"])]
            _knob: str = "book"
            mode: ClassVar[str] = "book-var"

            @command()
            def book_action(self) -> str:
                return "book-action"

            def describe(self) -> str:
                return "book"

        class Composed(KnobMixin, DeclaringBook):
            pass

        class Swapped(DeclaringBook, KnobMixin):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeMixin:
            knob = "mixin"
            tags: ClassVar[list[str]] = ["mixin-tags"]
            _knob = "mixin"
            mode = "mixin-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".mixin"}

            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class NativeBook:
            knob = "book"
            tags: ClassVar[list[str]] = ["book-tags"]
            _knob = "book"
            mode = "book-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".book"}

            def book_action(self) -> str:
                return "book-action"

            def describe(self) -> str:
                return "book"

        class NativeComposed(NativeMixin, NativeBook):
            pass

        class NativeSwapped(NativeBook, NativeMixin):
            pass

        assert Composed().knob == NativeComposed().knob == "mixin"
        assert Composed().tags == NativeComposed().tags == ["mixin-tags"]
        assert Composed()._knob == NativeComposed()._knob == "mixin"
        assert Composed.mode == NativeComposed.mode == "mixin-var"
        assert Composed().describe() == NativeComposed().describe() == "mixin"
        assert (
            Composed.model_config["env_file"] == NativeComposed.model_config["env_file"] == ".mixin"
        )

        assert Swapped().knob == NativeSwapped().knob == "book"
        assert Swapped().tags == NativeSwapped().tags == ["book-tags"]
        assert Swapped()._knob == NativeSwapped()._knob == "book"
        assert Swapped.mode == NativeSwapped.mode == "book-var"
        assert Swapped().describe() == NativeSwapped().describe() == "book"
        assert Swapped.model_config["env_file"] == NativeSwapped.model_config["env_file"] == ".book"

        expected = {
            "mix_action": ExpectedCommand(
                name="mix_action", command_type=types.MethodType, output="mixin-action"
            ),
            "book_action": ExpectedCommand(
                name="book_action", command_type=types.MethodType, output="book-action"
            ),
        }
        assert_commands(Composed(), expected, msg="Both declarations register (mixin first)")
        assert_commands(Swapped(), expected, msg="Both declarations register (book first)")

    def test_book_between_mixins_resolves_mro(self) -> None:
        # The book sandwiched: the leading mixin wins every conflicting kind,
        # the book beats the trailing mixin, and both mixins' sole-declared
        # kinds ride through. Config splits on position — a key the leading
        # mixin shares with Bakebook resolves to the mixin, the trailing
        # mixin's copy loses (Bakebook precedes it in the MRO, natively too).
        class SpaceBase(Bakebook):
            knob: str = "base"
            serial: str = "book-only"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class FirstMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_prefix="first_")

            knob: str = "first"
            tags: Annotated[list[str], Field(default_factory=lambda: ["first-tags"])]
            _knob: str = "first"
            mode: ClassVar[str] = "first-var"

            @command()
            def mix_action(self) -> str:
                return "first-action"

            def describe(self) -> str:
                return "first"

        class SecondMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".second", case_sensitive=True)

            knob: str = "second"
            tags: Annotated[list[str], Field(default_factory=lambda: ["second-tags"])]
            _knob: str = "second"
            mode: ClassVar[str] = "second-var"

            @command()
            def mix_action(self) -> str:
                return "second-action"

            def describe(self) -> str:
                return "second"

        class Composed(FirstMixin, SpaceBase, SecondMixin):
            pass

        class Swapped(SecondMixin, SpaceBase, FirstMixin):
            pass

        # Native mirror of the same shape resolves via the MRO. NativeBakebook
        # models Bakebook's own env_file declaration: the trailing mixin sits
        # after it in the MRO natively too, so it loses the shared key.
        class NativeBakebook:
            model_config: ClassVar[dict[str, str]] = {"env_file": ".env"}

        class NativeBase(NativeBakebook):
            knob = "base"
            serial = "book-only"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeFirst:
            knob = "first"
            tags: ClassVar[list[str]] = ["first-tags"]
            _knob = "first"
            mode = "first-var"
            model_config: ClassVar[dict[str, str]] = {"env_prefix": "first_"}

            def mix_action(self) -> str:
                return "first-action"

            def describe(self) -> str:
                return "first"

        class NativeSecond:
            knob = "second"
            tags: ClassVar[list[str]] = ["second-tags"]
            _knob = "second"
            mode = "second-var"
            model_config: ClassVar[dict[str, object]] = {
                "env_file": ".second",
                "case_sensitive": True,
            }

            def mix_action(self) -> str:
                return "second-action"

            def describe(self) -> str:
                return "second"

        # The composed mirrors restate the key-level resolution: plain
        # attribute lookup would take the first declarer's whole dict, but
        # config resolves per key.
        class NativeComposed(NativeFirst, NativeBase, NativeSecond):
            model_config: ClassVar[dict[str, object]] = {
                "env_prefix": "first_",
                "env_file": ".env",
                "case_sensitive": True,
            }

        class NativeSwapped(NativeSecond, NativeBase, NativeFirst):
            model_config: ClassVar[dict[str, object]] = {
                "env_prefix": "first_",
                "env_file": ".second",
                "case_sensitive": True,
            }

        assert Composed().knob == NativeComposed().knob == "first"
        assert Composed().tags == NativeComposed().tags == ["first-tags"]
        assert Composed()._knob == NativeComposed()._knob == "first"
        assert Composed.mode == NativeComposed.mode == "first-var"
        assert Composed().describe() == NativeComposed().describe() == "first"
        assert Composed().serial == NativeComposed().serial == "book-only"
        assert Composed().mix_action() == "first-action"

        assert Swapped().knob == NativeSwapped().knob == "second"
        assert Swapped().tags == NativeSwapped().tags == ["second-tags"]
        assert Swapped()._knob == NativeSwapped()._knob == "second"
        assert Swapped.mode == NativeSwapped.mode == "second-var"
        assert Swapped().describe() == NativeSwapped().describe() == "second"
        assert Swapped().serial == NativeSwapped().serial == "book-only"
        assert Swapped().mix_action() == "second-action"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="first-action"
                ),
            },
            msg="Leading mixin's command wins",
        )
        assert_commands(
            Swapped(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="second-action"
                ),
            },
            msg="Swapped: leading mixin's command wins",
        )

        # The kwargs path (pydantic-specific) still initializes the winning
        # side's fields.
        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Swapped(tags=["from-kwargs"]).tags == ["from-kwargs"]

        # Shared env_file key: the trailing mixin loses to Bakebook, the
        # leading one beats it.
        assert (
            Composed.model_config["env_file"] == NativeComposed.model_config["env_file"] == (".env")
        )
        assert (
            Swapped.model_config["env_file"] == NativeSwapped.model_config["env_file"] == ".second"
        )
        assert Composed.model_config["env_prefix"] == "first_"
        assert Swapped.model_config["env_prefix"] == "first_"
        assert Composed.model_config["case_sensitive"] is True
        assert Swapped.model_config["case_sensitive"] is True

    def test_book_before_two_mixins_resolves_mro(self) -> None:
        # The book first: it precedes both mixins in the MRO natively too, so
        # it wins every conflicting kind while the mixins still resolve among
        # themselves — the leftmost mixin takes the kinds only mixins
        # declare, and a config key shared with Bakebook stays Bakebook's.
        class SpaceBase(Bakebook):
            knob: str = "base"
            serial: str = "book-only"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class FirstMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_prefix="first_")

            knob: str = "first"
            tags: Annotated[list[str], Field(default_factory=lambda: ["first-tags"])]
            _knob: str = "first"
            mode: ClassVar[str] = "first-var"

            @command()
            def mix_action(self) -> str:
                return "first-action"

            def describe(self) -> str:
                return "first"

        class SecondMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".second", case_sensitive=True)

            knob: str = "second"
            tags: Annotated[list[str], Field(default_factory=lambda: ["second-tags"])]
            _knob: str = "second"
            mode: ClassVar[str] = "second-var"

            @command()
            def mix_action(self) -> str:
                return "second-action"

            def describe(self) -> str:
                return "second"

        class Composed(SpaceBase, FirstMixin, SecondMixin):
            pass

        class Swapped(SpaceBase, SecondMixin, FirstMixin):
            pass

        # Native mirror of the same shape resolves via the MRO. NativeBakebook
        # models Bakebook's own env_file declaration: both mixins trail it in
        # the MRO natively too, so the shared key stays Bakebook's.
        class NativeBakebook:
            model_config: ClassVar[dict[str, str]] = {"env_file": ".env"}

        class NativeBase(NativeBakebook):
            knob = "base"
            serial = "book-only"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeFirst:
            knob = "first"
            tags: ClassVar[list[str]] = ["first-tags"]
            _knob = "first"
            mode = "first-var"
            model_config: ClassVar[dict[str, str]] = {"env_prefix": "first_"}

            def mix_action(self) -> str:
                return "first-action"

            def describe(self) -> str:
                return "first"

        class NativeSecond:
            knob = "second"
            tags: ClassVar[list[str]] = ["second-tags"]
            _knob = "second"
            mode = "second-var"
            model_config: ClassVar[dict[str, object]] = {
                "env_file": ".second",
                "case_sensitive": True,
            }

            def mix_action(self) -> str:
                return "second-action"

            def describe(self) -> str:
                return "second"

        class NativeComposed(NativeBase, NativeFirst, NativeSecond):
            pass

        class NativeSwapped(NativeBase, NativeSecond, NativeFirst):
            pass

        # The book wins the shared kinds in either mixin order; the mixins
        # resolve the mixin-only kinds among themselves.
        assert Composed().knob == NativeComposed().knob == "base"
        assert Composed()._knob == NativeComposed()._knob == "base-default"
        assert Composed.mode == NativeComposed.mode == "book-var"
        assert Composed().describe() == NativeComposed().describe() == "book"
        assert Composed().tags == NativeComposed().tags == ["first-tags"]
        assert Composed().serial == NativeComposed().serial == "book-only"
        assert Composed().mix_action() == "first-action"

        assert Swapped().knob == NativeSwapped().knob == "base"
        assert Swapped()._knob == NativeSwapped()._knob == "base-default"
        assert Swapped.mode == NativeSwapped.mode == "book-var"
        assert Swapped().describe() == NativeSwapped().describe() == "book"
        assert Swapped().tags == NativeSwapped().tags == ["second-tags"]
        assert Swapped().serial == NativeSwapped().serial == "book-only"
        assert Swapped().mix_action() == "second-action"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="first-action"
                ),
            },
            msg="Leftmost mixin's command wins the shared name",
        )
        assert_commands(
            Swapped(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="second-action"
                ),
            },
            msg="Swapped: leftmost mixin's command wins the shared name",
        )

        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Swapped(tags=["from-kwargs"]).tags == ["from-kwargs"]

        # The shared env_file key stays Bakebook's in either mixin order;
        # each mixin's sole-declared keys survive.
        assert (
            Composed.model_config["env_file"] == NativeComposed.model_config["env_file"] == (".env")
        )
        assert (
            Swapped.model_config["env_file"] == NativeSwapped.model_config["env_file"] == (".env")
        )
        assert Composed.model_config["env_prefix"] == "first_"
        assert Swapped.model_config["env_prefix"] == "first_"
        assert Composed.model_config["case_sensitive"] is True
        assert Swapped.model_config["case_sensitive"] is True


class TestMixinChains:
    """
    Inheritance within mixins: a child mixin redeclares every kind, a
    plain child inherits them all, and two children of a shared mixin
    base resolve their conflicts through the MRO (the bug shape).
    """

    def test_mixin_chain_composes_with_book(self) -> None:
        class BaseMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".base-mix")

            shared: str = "base"
            tags: Annotated[list[str], Field(default_factory=lambda: ["base-tags"])]
            _shared: str = "base"
            mode: ClassVar[str] = "base-var"

            @command()
            def mix_action(self) -> str:
                return "base-action"

            def describe(self) -> str:
                return "base"

        class ChildMixin(BaseMixin):
            shared: str = "child"
            tags: Annotated[list[str], Field(default_factory=lambda: ["child-tags"])]
            _shared: str = "child"
            mode: ClassVar[str] = "child-var"

            @command()
            def mix_action(self) -> str:
                return "child-action"

            def describe(self) -> str:
                return "child"

        class PlainChildMixin(BaseMixin):
            pass

        class SpaceBase(Bakebook):
            pass

        class Composed(ChildMixin, SpaceBase):
            pass

        class Inherited(PlainChildMixin, SpaceBase):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            shared = "base"
            tags: ClassVar[list[str]] = ["base-tags"]
            _shared = "base"
            mode = "base-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".base-mix"}

            def mix_action(self) -> str:
                return "base-action"

            def describe(self) -> str:
                return "base"

        class NativeChild(NativeBase):
            shared = "child"
            tags: ClassVar[list[str]] = ["child-tags"]
            _shared = "child"
            mode = "child-var"

            def mix_action(self) -> str:
                return "child-action"

            def describe(self) -> str:
                return "child"

        class NativePlainChild(NativeBase):
            pass

        class NativeSpace:
            pass

        class NativeComposed(NativeChild, NativeSpace):
            pass

        class NativeInherited(NativePlainChild, NativeSpace):
            pass

        assert Composed().shared == NativeComposed().shared == "child"
        assert Composed().tags == NativeComposed().tags == ["child-tags"]
        assert Composed()._shared == NativeComposed()._shared == "child"
        assert Composed.mode == NativeComposed.mode == "child-var"
        assert Composed().describe() == NativeComposed().describe() == "child"
        assert Composed().mix_action() == "child-action"
        assert (
            Composed.model_config["env_file"]
            == NativeComposed.model_config["env_file"]
            == ".base-mix"
        )

        assert Inherited().shared == NativeInherited().shared == "base"
        assert Inherited().tags == NativeInherited().tags == ["base-tags"]
        assert Inherited()._shared == NativeInherited()._shared == "base"
        assert Inherited.mode == NativeInherited.mode == "base-var"
        assert Inherited().describe() == NativeInherited().describe() == "base"
        assert Inherited().mix_action() == "base-action"

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="child-action"
                ),
            },
            msg="Child mixin's redeclared command wins",
        )
        assert_commands(
            Inherited(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="base-action"
                ),
            },
            msg="Plain child mixin inherits the base registration",
        )

    def test_mixin_diamond_resolves_mro(self) -> None:
        # Two children of a shared mixin base: the overriding child wins in
        # either order — in the plain-first bug shape the sibling's inherited
        # snapshots must not shadow its declarations (pydantic#13678/#11700
        # transposed into mixin land).
        class BaseMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_prefix="base_")

            knob: str = "base-mix"
            tags: Annotated[list[str], Field(default_factory=lambda: ["base-tags"])]
            _knob: str = "base-default"
            mode: ClassVar[str] = "base-var"

            @command()
            def mix_action(self) -> str:
                return "base-action"

            def describe(self) -> str:
                return "base"

        class OverrideMixin(BaseMixin):
            knob: str = "override-mix"
            tags: Annotated[list[str], Field(default_factory=lambda: ["override-tags"])]
            _knob: str = "override"
            mode: ClassVar[str] = "override-var"

            @command()
            def mix_action(self) -> str:
                return "override-action"

            def describe(self) -> str:
                return "override"

        class PlainMixin(BaseMixin):
            pass

        class SpaceBase(Bakebook):
            pass

        class Composed(OverrideMixin, PlainMixin, SpaceBase):
            pass

        class Swapped(PlainMixin, OverrideMixin, SpaceBase):
            pass

        # Native mirror of the same shape resolves via the MRO.
        class NativeBase:
            knob = "base-mix"
            tags: ClassVar[list[str]] = ["base-tags"]
            _knob = "base-default"
            mode = "base-var"
            model_config: ClassVar[dict[str, str]] = {"env_prefix": "base_"}

            def mix_action(self) -> str:
                return "base-action"

            def describe(self) -> str:
                return "base"

        class NativeOverride(NativeBase):
            knob = "override-mix"
            tags: ClassVar[list[str]] = ["override-tags"]
            _knob = "override"
            mode = "override-var"

            def mix_action(self) -> str:
                return "override-action"

            def describe(self) -> str:
                return "override"

        class NativePlain(NativeBase):
            pass

        class NativeSpace:
            pass

        class NativeComposed(NativeOverride, NativePlain, NativeSpace):
            pass

        class NativeSwapped(NativePlain, NativeOverride, NativeSpace):
            pass

        for bakebook, native in ((Composed(), NativeComposed()), (Swapped(), NativeSwapped())):
            label = type(bakebook).__name__
            assert bakebook.knob == native.knob == "override-mix", label
            assert bakebook.tags == native.tags == ["override-tags"], label
            assert bakebook._knob == native._knob == "override", label
            assert type(bakebook).mode == native.mode == "override-var", label
            assert bakebook.describe() == native.describe() == "override", label
            assert bakebook.mix_action() == "override-action", label
            assert (
                type(bakebook).model_config["env_prefix"]
                == native.model_config["env_prefix"]
                == "base_"
            ), label

        assert_commands(
            Composed(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="override-action"
                ),
            },
            msg="Overriding mixin's command wins",
        )
        assert_commands(
            Swapped(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="override-action"
                ),
            },
            msg="Swapped: the overriding mixin still wins",
        )

        assert Composed(knob="from-kwargs").knob == "from-kwargs"
        assert Swapped(tags=["from-kwargs"]).tags == ["from-kwargs"]


class TestLayeredComposition:
    """
    Layered composition: a second composition layered onto an already
    composed base. The fix runs per subclass, so the second pass re-merges
    the first pass's resolved snapshot — resolution follows the final MRO,
    not layer order.
    """

    def test_compose_onto_composed_class(self) -> None:
        class SpaceBase(Bakebook):
            knob: str = "base"
            serial: str = "book-only"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_prefix="knob_")

            knob: str = "knob-mix"
            tags: Annotated[list[str], Field(default_factory=lambda: ["knob-tags"])]
            _knob: str = "knob-mix"
            mode: ClassVar[str] = "knob-var"

            @command()
            def mix_action(self) -> str:
                return "knob-action"

            def describe(self) -> str:
                return "knob"

        class ExtraMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".extra")

            knob: str = "extra-mix"
            bonus: str = "bonus"
            _knob: str = "extra-mix"
            mode: ClassVar[str] = "extra-var"

            @command()
            def mix_action(self) -> str:
                return "extra-action"

            def describe(self) -> str:
                return "extra"

        # First composition: the mixin baked into a reusable base.
        class Base(KnobMixin, SpaceBase):
            pass

        # Second composition layered on top, in both orders.
        class Child(Base, ExtraMixin):
            pass

        class ChildSwapped(ExtraMixin, Base):
            pass

        # Native mirror of the same shape resolves via the MRO. NativeBakebook
        # models Bakebook's own env_file declaration and NativeMixinBase the
        # shared mixin root: the diamond pins the late mixin between the
        # baked-in mixin and the book, ahead of Bakebook — natively too.
        class NativeBakebook:
            model_config: ClassVar[dict[str, str]] = {"env_file": ".env"}

        class NativeMixinBase:
            pass

        class NativeBase(NativeBakebook):
            knob = "base"
            serial = "book-only"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeKnobMixin(NativeMixinBase):
            knob = "knob-mix"
            tags: ClassVar[list[str]] = ["knob-tags"]
            _knob = "knob-mix"
            mode = "knob-var"
            model_config: ClassVar[dict[str, str]] = {"env_prefix": "knob_"}

            def mix_action(self) -> str:
                return "knob-action"

            def describe(self) -> str:
                return "knob"

        class NativeExtraMixin(NativeMixinBase):
            knob = "extra-mix"
            bonus = "bonus"
            _knob = "extra-mix"
            mode = "extra-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".extra"}

            def mix_action(self) -> str:
                return "extra-action"

            def describe(self) -> str:
                return "extra"

        # The composed mirrors restate the key-level resolution at each layer.
        class NativeComposedBase(NativeKnobMixin, NativeBase):
            model_config: ClassVar[dict[str, object]] = {
                "env_prefix": "knob_",
                "env_file": ".env",
            }

        class NativeChild(NativeComposedBase, NativeExtraMixin):
            # ExtraMixin rides at NativeMixinBase's slot, ahead of
            # NativeBakebook, so it wins the shared key.
            model_config: ClassVar[dict[str, object]] = {
                "env_prefix": "knob_",
                "env_file": ".extra",
            }

        class NativeChildSwapped(NativeExtraMixin, NativeComposedBase):
            model_config: ClassVar[dict[str, object]] = {
                "env_prefix": "knob_",
                "env_file": ".extra",
            }

        # The first pass resolves on its own.
        assert Base().knob == NativeComposedBase().knob == "knob-mix"
        assert Base().tags == NativeComposedBase().tags == ["knob-tags"]
        assert Base()._knob == NativeComposedBase()._knob == "knob-mix"
        assert Base.mode == NativeComposedBase.mode == "knob-var"
        assert Base().describe() == NativeComposedBase().describe() == "knob"
        assert Base().serial == NativeComposedBase().serial == "book-only"
        assert Base().mix_action() == "knob-action"
        assert Base.model_config["env_prefix"] == "knob_"
        assert Base.model_config["env_file"] == ".env"

        # Child: the late mixin sits after Base's whole chain, so the baked-in
        # mixin keeps every shared kind while the late mixin's sole-declared
        # kinds ride through.
        assert Child().knob == NativeChild().knob == "knob-mix"
        assert Child().tags == NativeChild().tags == ["knob-tags"]
        assert Child()._knob == NativeChild()._knob == "knob-mix"
        assert Child.mode == NativeChild.mode == "knob-var"
        assert Child().describe() == NativeChild().describe() == "knob"
        assert Child().serial == NativeChild().serial == "book-only"
        assert Child().mix_action() == "knob-action"
        assert Child().bonus == NativeChild().bonus == "bonus"

        # ChildSwapped: the late mixin precedes Base's whole chain, so it wins
        # the shared kinds while the baked-in mixin's sole-declared kinds ride.
        assert ChildSwapped().knob == NativeChildSwapped().knob == "extra-mix"
        assert ChildSwapped().tags == NativeChildSwapped().tags == ["knob-tags"]
        assert ChildSwapped()._knob == NativeChildSwapped()._knob == "extra-mix"
        assert ChildSwapped.mode == NativeChildSwapped.mode == "extra-var"
        assert ChildSwapped().describe() == NativeChildSwapped().describe() == "extra"
        assert ChildSwapped().serial == NativeChildSwapped().serial == "book-only"
        assert ChildSwapped().mix_action() == "extra-action"
        assert ChildSwapped().bonus == NativeChildSwapped().bonus == "bonus"

        assert_commands(
            Base(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="knob-action"
                ),
            },
            msg="First composition's command registers",
        )
        assert_commands(
            Child(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="knob-action"
                ),
            },
            msg="Baked-in mixin's command survives the second layer",
        )
        assert_commands(
            ChildSwapped(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="extra-action"
                ),
            },
            msg="Late mixin's command wins when it leads",
        )

        # The kwargs path (pydantic-specific) still initializes fields at both
        # layers.
        assert Base(knob="from-kwargs").knob == "from-kwargs"
        assert Child(knob="from-kwargs").knob == "from-kwargs"
        assert Child(bonus="from-kwargs").bonus == "from-kwargs"
        assert ChildSwapped(tags=["from-kwargs"]).tags == ["from-kwargs"]

        # Shared env_file key: the diamond pulls the late mixin ahead of
        # Bakebook in the MRO (BakebookMixin rides between the baked-in mixin
        # and the book), so the late mixin's key wins in both orders —
        # natively too.
        assert Child.model_config["env_file"] == NativeChild.model_config["env_file"] == ".extra"
        assert (
            ChildSwapped.model_config["env_file"]
            == NativeChildSwapped.model_config["env_file"]
            == ".extra"
        )


class TestRedeclaration:
    """
    Redeclaration: a subclass of the composed class redeclares every kind
    on top of the mixin composition.
    """

    def test_subclass_redeclare_survives_mixin_composition(self) -> None:
        class KnobMixin(BakebookMixin):
            model_config = SettingsConfigDict(env_file=".myenv")

            knob: str = "mixin"
            tags: Annotated[list[str], Field(default_factory=lambda: ["mixin-tags"])]
            _knob: str = "mixin"
            mode: ClassVar[str] = "mixin-var"

            @command()
            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"
            mode: ClassVar[str] = "book-var"

            def describe(self) -> str:
                return "book"

        class Composed(KnobMixin, SpaceBase):
            pass

        class Sub(Composed):
            knob: str = "sub"
            tags: Annotated[list[str], Field(default_factory=lambda: ["sub-tags"])]
            _knob: str = "sub"
            mode: ClassVar[str] = "sub-var"

            def mix_action(self) -> str:
                return "sub-action"

            def describe(self) -> str:
                return "sub"

        # Native mirror of the same shape resolves via the MRO.
        class NativeMixin:
            knob = "mixin"
            tags: ClassVar[list[str]] = ["mixin-tags"]
            _knob = "mixin"
            mode = "mixin-var"
            model_config: ClassVar[dict[str, str]] = {"env_file": ".myenv"}

            def mix_action(self) -> str:
                return "mixin-action"

            def describe(self) -> str:
                return "mixin"

        class NativeBase:
            knob = "base"
            _knob = "base-default"
            mode = "book-var"

            def describe(self) -> str:
                return "book"

        class NativeComposed(NativeMixin, NativeBase):
            pass

        class NativeSub(NativeComposed):
            knob = "sub"
            tags: ClassVar[list[str]] = ["sub-tags"]
            _knob = "sub"
            mode = "sub-var"

            def mix_action(self) -> str:
                return "sub-action"

            def describe(self) -> str:
                return "sub"

        assert Composed().knob == NativeComposed().knob == "mixin"
        assert Composed().tags == NativeComposed().tags == ["mixin-tags"]
        assert Composed()._knob == NativeComposed()._knob == "mixin"
        assert Composed.mode == NativeComposed.mode == "mixin-var"
        assert Composed().describe() == NativeComposed().describe() == "mixin"

        bakebook = Sub()
        assert bakebook.knob == NativeSub().knob == "sub"
        assert bakebook.tags == NativeSub().tags == ["sub-tags"]
        assert bakebook._knob == NativeSub()._knob == "sub"
        assert Sub.mode == NativeSub.mode == "sub-var"
        assert bakebook.describe() == NativeSub().describe() == "sub"
        assert bakebook.mix_action() == "sub-action"
        assert Sub.model_config["env_file"] == NativeSub.model_config["env_file"] == ".myenv"

        # The kwargs path (pydantic-specific) initializes the redeclared field.
        assert Sub(knob="from-kwargs").knob == "from-kwargs"
        assert Sub(tags=["from-kwargs"]).tags == ["from-kwargs"]

        assert_commands(
            Sub(),
            {
                "mix_action": ExpectedCommand(
                    name="mix_action", command_type=types.MethodType, output="sub-action"
                ),
            },
            msg="Undecorated override inherits the mixin's registration",
        )


class TestMixinKindFlips:
    """
    Kind flips between mixin and book: the same name declared as a plain
    method on one side and a @command on the other. The MRO decides the
    callable, and the name registers exactly once — the marker search
    walks the MRO, so even a shadowing plain method registers
    (undecorated-override semantics). The flip is the pattern, so these
    stay method/command-focused.
    """

    def test_method_to_command_flip_follows_mro(self) -> None:
        # The mixin's plain method against the book's @command on the same
        # name: the MRO decides the callable in either order and the name
        # registers exactly once.
        class PlainMethodMixin(BakebookMixin):
            def action(self) -> str:
                return "mixin-plain"

        class CommandBook(Bakebook):
            @command()
            def action(self) -> str:
                return "book-command"

        class Composed(PlainMethodMixin, CommandBook):
            pass

        class Swapped(CommandBook, PlainMethodMixin):
            pass

        # Native mirror: natively a @command is just a method, so the flip
        # reduces to method-order resolution.
        class NativeMixin:
            def action(self) -> str:
                return "mixin-plain"

        class NativeBook:
            def action(self) -> str:
                return "book-command"

        class NativeComposed(NativeMixin, NativeBook):
            pass

        class NativeSwapped(NativeBook, NativeMixin):
            pass

        assert Composed().action() == NativeComposed().action() == "mixin-plain"
        assert Swapped().action() == NativeSwapped().action() == "book-command"
        assert len(Composed()._app.registered_commands) == 1
        assert len(Swapped()._app.registered_commands) == 1

        assert_commands(
            Composed(),
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="mixin-plain"
                ),
            },
            msg="Mixin's shadowing plain method registers via the book's marker",
        )
        assert_commands(
            Swapped(),
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="book-command"
                ),
            },
            msg="Book's @command registers when it wins the MRO",
        )

    def test_command_to_method_flip_follows_mro(self) -> None:
        # The reverse flip: the mixin's @command against the book's plain
        # method. Same invariant — the MRO decides the callable, the name
        # registers once.
        class CommandMixin(BakebookMixin):
            @command()
            def action(self) -> str:
                return "mixin-command"

        class PlainMethodBook(Bakebook):
            def action(self) -> str:
                return "book-plain"

        class Composed(CommandMixin, PlainMethodBook):
            pass

        class Swapped(PlainMethodBook, CommandMixin):
            pass

        # Native mirror: natively a @command is just a method, so the flip
        # reduces to method-order resolution.
        class NativeMixin:
            def action(self) -> str:
                return "mixin-command"

        class NativeBook:
            def action(self) -> str:
                return "book-plain"

        class NativeComposed(NativeMixin, NativeBook):
            pass

        class NativeSwapped(NativeBook, NativeMixin):
            pass

        assert Composed().action() == NativeComposed().action() == "mixin-command"
        assert Swapped().action() == NativeSwapped().action() == "book-plain"
        assert len(Composed()._app.registered_commands) == 1
        assert len(Swapped()._app.registered_commands) == 1

        assert_commands(
            Composed(),
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="mixin-command"
                ),
            },
            msg="Mixin's @command registers when it wins the MRO",
        )
        assert_commands(
            Swapped(),
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="book-plain"
                ),
            },
            msg="Book's shadowing plain method registers via the mixin's marker",
        )

    def test_same_name_command_conflict_resolves_mro(self) -> None:
        # Both sides decorate the same name: the MRO-first callable is the
        # one registered — no conflict error, exactly one registration.
        class CommandMixin(BakebookMixin):
            @command()
            def action(self) -> str:
                return "mixin-action"

        class CommandBook(Bakebook):
            @command()
            def action(self) -> str:
                return "book-action"

        class Composed(CommandMixin, CommandBook):
            pass

        class Swapped(CommandBook, CommandMixin):
            pass

        # Native mirror: natively a @command is just a method, so the
        # conflict reduces to method-order resolution.
        class NativeMixin:
            def action(self) -> str:
                return "mixin-action"

        class NativeBook:
            def action(self) -> str:
                return "book-action"

        class NativeComposed(NativeMixin, NativeBook):
            pass

        class NativeSwapped(NativeBook, NativeMixin):
            pass

        assert Composed().action() == NativeComposed().action() == "mixin-action"
        assert Swapped().action() == NativeSwapped().action() == "book-action"

        assert_commands(
            Composed(),
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="mixin-action"
                ),
            },
            msg="Mixin's @command wins the shared name",
        )
        assert_commands(
            Swapped(),
            {
                "action": ExpectedCommand(
                    name="action", command_type=types.MethodType, output="book-action"
                ),
            },
            msg="Swapped: book's @command wins the shared name",
        )


class TestGenericMixin:
    """
    Generic mixins: a parametrized bundle substitutes typevars through
    machinery the declarer walk cannot see, so alias claims are asserted
    directly. The alias hazard is field-specific; all-kind asserts here
    would be vacuous, so these pins stay field-focused.
    """

    def test_parametrized_mixin_base_no_raise(self) -> None:
        # Parametrized generic mixin bases fill fields via generic machinery,
        # not class-body annotations; composition resolves the substituted copy.
        class GenericValueMixin(BakebookMixin, Generic[E]):
            value: E
            _secret: str = "mix"

        class SpaceBase(Bakebook):
            other: str = "other"

        class Composed(GenericValueMixin[str], SpaceBase):
            pass

        assert Composed.__pydantic_fields__["value"].annotation is str
        bakebook = Composed(value="from-kwargs", other="from-kwargs")
        assert bakebook.value == "from-kwargs"
        assert bakebook.other == "from-kwargs"
        assert bakebook._secret == "mix"

    def test_generic_mixin_bug_shape_resolves_mro(self) -> None:
        # The plain sibling mixin's inherited snapshot no longer beats the
        # alias's substituted override, in either order.
        class BaseMixin(BakebookMixin):
            knob: str = "base-mix"
            _knob: str = "base-default"

        class GenericOverrideMixin(BaseMixin, Generic[E]):
            knob: E
            _knob: str = "override"

        class PlainMixin(BaseMixin):
            pass

        class SpaceBase(Bakebook):
            pass

        class Composed(GenericOverrideMixin[str], PlainMixin, SpaceBase):
            pass

        class Swapped(PlainMixin, GenericOverrideMixin[str], SpaceBase):
            pass

        for model in (Composed, Swapped):
            label = model.__name__
            # The alias's substituted copy wins — not the defaulted base field.
            assert model.__pydantic_fields__["knob"].is_required(), label
            bakebook = model(knob="override")
            assert bakebook.knob == "override", label
            assert bakebook._knob == "override", label

    def test_generic_mixin_alias_does_not_claim_parallel_branch_field(self) -> None:
        # 'knob' comes from the book branch, so the mixin alias does not
        # claim it — the space's override survives.
        class SpaceBase(Bakebook):
            knob: str = "base"
            _knob: str = "base-default"

        class OverrideSpace(SpaceBase):
            knob: str = "override"
            _knob: str = "override"

        class GenericBundleMixin(BakebookMixin, Generic[E]):
            value: E

        class Swapped(GenericBundleMixin[str], OverrideSpace):
            pass

        # Native mirror of the knob resolution ('value' is generic machinery).
        class NativeBase:
            knob = "base"
            _knob = "base-default"

        class NativeOverride(NativeBase):
            knob = "override"
            _knob = "override"

        class NativeMixin:
            pass

        class NativeSwapped(NativeMixin, NativeOverride):
            pass

        bakebook = Swapped(value="from-kwargs")
        assert bakebook.knob == NativeSwapped().knob == "override"
        assert bakebook._knob == NativeSwapped()._knob == "override"
        assert bakebook.value == "from-kwargs"

    def test_generic_mixin_subclass_chain_no_raise(self) -> None:
        # Substitution flows through an unparametrized intermediate mixin.
        class GenericValueMixin(BakebookMixin, Generic[E]):
            value: E

        class TypedBundle(GenericValueMixin[str]):
            extra: str = "extra"

        class SpaceBase(Bakebook):
            pass

        class Composed(TypedBundle, SpaceBase):
            pass

        assert Composed.__pydantic_fields__["value"].annotation is str
        bakebook = Composed(value="from-kwargs")
        assert bakebook.value == "from-kwargs"
        assert bakebook.extra == "extra"

    def test_two_mixin_aliases_first_claim_wins(self) -> None:
        class GenericValueMixin(BakebookMixin, Generic[E]):
            value: E

        class BranchA(GenericValueMixin[E]):
            pass

        class BranchB(GenericValueMixin[E]):
            pass

        class SpaceBase(Bakebook):
            pass

        # Both branches parametrize the shared origin: legal as pydantic
        # aliases at runtime, inconsistent to the static checker.
        class Composed(BranchA[str], BranchB[int], SpaceBase):  # ty: ignore[invalid-generic-class]
            pass

        class Swapped(BranchB[int], BranchA[str], SpaceBase):  # ty: ignore[invalid-generic-class]
            pass

        # The first alias's claim stands; the second does not re-claim.
        assert Composed.__pydantic_fields__["value"].annotation is str
        assert Swapped.__pydantic_fields__["value"].annotation is int
