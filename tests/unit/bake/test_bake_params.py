from bake import params


def test_bake_params_exports() -> None:
    assert params.VerboseBool is not None
