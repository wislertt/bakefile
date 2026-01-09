import typer


def validate_file_name(file_name: str) -> str:
    if "/" in file_name or "\\" in file_name:
        raise typer.BadParameter(f"File name must not contain path separators: {file_name}")
    if not file_name.endswith(".py"):
        raise typer.BadParameter(f"File name must end with .py: {file_name}")
    return file_name


def validate_file_name_callback(value: str) -> str:
    return validate_file_name(file_name=value)
