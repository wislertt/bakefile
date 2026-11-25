from bakelib import suppress
from tests.utils.cli import CaptureOutput, RunCli, run_cli
from tests.utils.fixtures import (
    complex_vars_project,
    ctx_test_project,
    disable_colors,
    disable_script_env_warning,
    empty_project_folder,
    empty_project_folder_no_inline,
    get_project_env,
    hide_dotenv_file,
    isolate_global_config_dir,
    isolate_virtual_env,
    isolated_uv_cache,
    no_bakebook_dir,
    no_bakefile_dir,
    no_stray_parent_bakefile,
    prevent_reinvocation,
    remove_test_script_envs,
    reset_cwd,
    uv_project_folder,
    uv_project_folder_with_deps,
    uv_project_folder_without_dep,
)
from tests.utils.misc import (
    auto_cleanup_keyring,
    examples_python_package_dir,
    examples_simple_dir,
    mock_ctx,
    reset_all_logger_state,
)


def pytest_configure() -> None:
    suppress.all()


__all__ = [
    "CaptureOutput",
    "RunCli",
    "auto_cleanup_keyring",
    "complex_vars_project",
    "ctx_test_project",
    "disable_colors",
    "disable_script_env_warning",
    "empty_project_folder",
    "empty_project_folder_no_inline",
    "examples_python_package_dir",
    "examples_simple_dir",
    "get_project_env",
    "hide_dotenv_file",
    "isolate_global_config_dir",
    "isolate_virtual_env",
    "isolated_uv_cache",
    "mock_ctx",
    "no_bakebook_dir",
    "no_bakefile_dir",
    "no_stray_parent_bakefile",
    "prevent_reinvocation",
    "remove_test_script_envs",
    "reset_all_logger_state",
    "reset_cwd",
    "run_cli",
    "uv_project_folder",
    "uv_project_folder_with_deps",
    "uv_project_folder_without_dep",
]
