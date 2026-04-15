from pathlib import Path

# Default value
DEFAULT_CHDIR = Path(".")
DEFAULT_FILE_NAME = "bakefile.py"
DEFAULT_FILE_NAME_BASE = DEFAULT_FILE_NAME.replace(".py", "")
DEFAULT_BAKEBOOK_NAME = "bakebook"
DEFAULT_IS_CHAIN_COMMAND = False
DEFAULT_BAKE_LOG_BASE = "warning,bake=debug,bakelib=debug"
DEFAULT_BAKE_LOG_VERBOSITY = 0
DEFAULT_DRY_RUN = False
DEFAULT_BAKE_LOG_PRETTY = True


def get_default_bake_log(file_name_base: str = DEFAULT_FILE_NAME_BASE) -> str:
    module_name = file_name_base.replace(".py", "")
    return f"{DEFAULT_BAKE_LOG_BASE},{module_name}=debug"


DEFAULT_BAKE_LOG = get_default_bake_log()

# CLI command names
CMD_BAKE = "bake"
CMD_BAKEFILE = "bakefile"
CMD_INIT = "init"
CMD_ADD_INLINE = "add-inline"
CMD_LINT = "lint"

# Bakefile app command name
GET_BAKEFILE_OBJECT = "get_bakefile_object"

# Others
BAKEBOOK_NAME_IN_SAMPLES = "__bakebook__"
BAKE_COMMAND_KWARGS = "_bake_command_kwargs"
