from bakelib import params


def test_bakelib_params_exports() -> None:
    assert params.PublishTokenOption is not None
    assert params.PublishVersionOption is not None
    assert params.DeployVersionOption is not None
