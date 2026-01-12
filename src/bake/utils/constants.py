from pathlib import Path

# Default value
DEFAULT_CHDIR = Path(".")
DEFAULT_FILE_NAME = "bakefile.py"
DEFAULT_BAKEBOOK_NAME = "bakebook"
DEFAULT_IS_CHAIN_COMMAND = False

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
