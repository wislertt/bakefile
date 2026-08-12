from bake.ui import style


def test_span_wraps_with_given_style() -> None:
    assert style.span("done", "magenta") == "[magenta]done[/magenta]"


def test_bold_green_wraps_with_bold_green_markup() -> None:
    assert style.bold_green("passed") == "[bold green]passed[/bold green]"


def test_bold_blue_wraps_with_bold_blue_markup() -> None:
    assert style.bold_blue("running") == "[bold blue]running[/bold blue]"


def test_dim_wraps_with_dim_markup() -> None:
    assert style.dim("secondary") == "[dim]secondary[/dim]"


def test_code_wraps_in_backticks_with_cyan() -> None:
    assert style.code("bake test") == "`[cyan]bake test[/cyan]`"
