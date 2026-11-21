# bakelib extends bake: the dependency runs one way

`bakelib` is built on top of `bake`, so `bakelib` imports `bake` and `bake` never imports `bakelib`. Anything the core needs lives in `bake`, even when `bakelib` uses it too. Downstream projects import `bakelib` for its Spaces, so reversing the direction later would break them.

The alternative was one package where the core could reach the prebuilt Spaces. That would make the core depend on code it does not need to run a `bakefile.py`. `bakelib` stays optional, installed with the `lib` extra, so a plain `bakefile` install carries no Space code. `tests/unit/bake/test_no_bakelib_import.py` enforces the rule.
