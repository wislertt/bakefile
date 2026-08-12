BOLD_GREEN = "bold green"
BOLD_BLUE = "bold blue"
BLUE = "blue"


def span(message: str, style: str) -> str:
    return f"[{style}]{message}[/{style}]"


def bold_green(message: str) -> str:
    return span(message, BOLD_GREEN)


def bold_blue(message: str) -> str:
    return span(message, BOLD_BLUE)


def dim(message: str) -> str:
    return span(message, "dim")


def code(message: str) -> str:
    return f"`{span(message, 'cyan')}`"
