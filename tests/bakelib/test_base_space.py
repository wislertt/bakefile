from bake import Bakebook
from bakelib.space.base import BaseSpace


def test_base_space_is_bakebook() -> None:
    assert issubclass(BaseSpace, Bakebook)
