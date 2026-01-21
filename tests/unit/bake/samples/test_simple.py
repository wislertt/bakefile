from bake.samples.simple import hello


def test_hello() -> None:
    hello()
    hello(name="Alice")
