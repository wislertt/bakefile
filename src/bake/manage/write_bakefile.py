import types
from pathlib import Path

from bake.utils.constants import BAKEBOOK_NAME_IN_SAMPLES


def write_bakefile(
    bakefile_path: Path, bakebook_name: str, sample_module: types.ModuleType
) -> None:
    if not hasattr(sample_module, BAKEBOOK_NAME_IN_SAMPLES):
        raise ValueError(
            f"Module `{sample_module.__name__}` must have `{BAKEBOOK_NAME_IN_SAMPLES}` attribute"
        )

    if sample_module.__file__ is None:
        raise ValueError(f"Could not find `{sample_module.__name__}`")

    original_bakefile_content = Path(sample_module.__file__).read_text()
    customized_content = original_bakefile_content.replace(BAKEBOOK_NAME_IN_SAMPLES, bakebook_name)
    bakefile_path.write_text(customized_content)
