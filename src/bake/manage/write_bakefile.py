import types
from pathlib import Path

from bake.samples import simple
from bake.utils.constants import BAKEBOOK_NAME_IN_SAMPLES

# Allowed sample modules
# This dictionary acts as a whitelist for security - only these modules can be used
ALLOWED_SAMPLE_MODULES: dict[str, types.ModuleType] = {
    simple.__name__: simple,
}


def write_bakefile(
    bakefile_path: Path, bakebook_name: str, sample_module: types.ModuleType
) -> None:
    if not hasattr(sample_module, BAKEBOOK_NAME_IN_SAMPLES):
        raise ValueError(
            f"Module `{sample_module.__name__}` must have `{BAKEBOOK_NAME_IN_SAMPLES}` attribute"
        )

    module_name = sample_module.__name__
    if module_name not in ALLOWED_SAMPLE_MODULES:
        raise ValueError(
            f"Module `{module_name}` is not in the allowed sample modules list. "
            f"Allowed modules: {list(ALLOWED_SAMPLE_MODULES.keys())}"
        )

    allowed_module = ALLOWED_SAMPLE_MODULES[module_name]
    if sample_module is not allowed_module:
        raise ValueError(f"Module `{module_name}` does not match the allowed module object")

    if allowed_module.__file__ is None:
        raise ValueError(f"Could not find file for module `{module_name}`")

    source_file_path = Path(allowed_module.__file__)
    original_bakefile_content = source_file_path.read_text()
    customized_content = original_bakefile_content.replace(BAKEBOOK_NAME_IN_SAMPLES, bakebook_name)
    bakefile_path.write_text(customized_content)
