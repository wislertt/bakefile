from pathlib import Path

from bake.manage.write_bakefile import write_bakefile
from bake.samples import simple
from bake.utils.constants import (
    BAKEBOOK_NAME_IN_SAMPLES,
    DEFAULT_FILE_NAME,
)


def test_write_bakefile(tmp_path: Path) -> None:
    bakebook_name = "my_bakebook"
    bakefile_path = tmp_path / DEFAULT_FILE_NAME

    write_bakefile(
        bakefile_path=bakefile_path,
        bakebook_name=bakebook_name,
        sample_module=simple,
    )

    assert bakefile_path.exists()

    content = bakefile_path.read_text()
    assert bakebook_name in content
    assert BAKEBOOK_NAME_IN_SAMPLES not in content
