# from pathlib import Path

# import orjson
# import pytest
# import yaml

# from bake import Bakebook
# from bake.cli.bakefile.export import (
#     DotEnvExportFormatter,
#     JsonExportFormatter,
#     ShExportFormatter,
#     YamlExportFormatter,
#     _export,
# )
# from bake.ui.logger import strip_ansi
# from bake.utils.constants import CMD_BAKEFILE
# from tests.conftest import RunCli
# from tests.utils.bakefiles.complex_vars import ComplexVarsBakebook


# class TestFormatSh:
#     def test_format_sh_with_primitives(self) -> None:
#         class SimpleBakebook(Bakebook):
#             name: str = "app"
#             count: int = 42
#             enabled: bool = True

#         bakebook = SimpleBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = ShExportFormatter()
#         result = formatter(data)

#         assert "export NAME=app" in result
#         assert "export COUNT=42" in result
#         assert "export ENABLED=true" in result

#     def test_format_sh_with_complex_types(self) -> None:
#         bakebook = ComplexVarsBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = ShExportFormatter()
#         result = formatter(data)

#         assert "export NAME=app" in result
#         assert 'export TAGS=\'["a","b"]\'' in result
#         assert 'export CONFIG=\'{"key":"value"}\'' in result

#     def test_format_sh_with_nullable(self) -> None:
#         bakebook = ComplexVarsBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = ShExportFormatter()
#         result = formatter(data)

#         assert "export NULLABLE=" in result

#     def test_format_sh_empty_bakebook(self) -> None:
#         class EmptyBakebook(Bakebook):
#             pass

#         bakebook = EmptyBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = ShExportFormatter()
#         result = formatter(data)

#         assert result == ""


# class TestFormatDotenv:
#     def test_format_dotenv_with_primitives(self) -> None:
#         class SimpleBakebook(Bakebook):
#             name: str = "app"
#             count: int = 42

#         bakebook = SimpleBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = DotEnvExportFormatter()
#         result = formatter(data)

#         assert "NAME=app" in result
#         assert "COUNT=42" in result
#         # No export keyword
#         assert "export" not in result.lower()

#     def test_format_dotenv_with_complex_types(self) -> None:
#         bakebook = ComplexVarsBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = DotEnvExportFormatter()
#         result = formatter(data)

#         assert "NAME=app" in result
#         assert 'TAGS="[\\"a\\",\\"b\\"]"' in result
#         assert 'CONFIG="{\\"key\\":\\"value\\"}"' in result


# class TestFormatJson:
#     def test_format_json_with_all_types(self) -> None:
#         bakebook = ComplexVarsBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = JsonExportFormatter()
#         result = formatter(data)

#         parsed = orjson.loads(result)

#         # Verify critical original fields
#         assert parsed["name"] == "app"
#         assert parsed["count"] == 42
#         assert parsed["enabled"] is True
#         assert parsed["tags"] == ["a", "b"]
#         assert parsed["config"] == {"key": "value"}
#         assert parsed["nullable"] is None

#         # Verify edge case fields exist
#         assert "empty_string" in parsed
#         assert "zero" in parsed
#         assert "negative" in parsed
#         assert "scientific" in parsed
#         assert "empty_list" in parsed
#         assert "empty_dict" in parsed
#         assert "unicode" in parsed
#         assert "emoji" in parsed

#     def test_format_json_empty_bakebook(self) -> None:
#         class EmptyBakebook(Bakebook):
#             pass

#         bakebook = EmptyBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = JsonExportFormatter()
#         result = formatter(data)

#         parsed = orjson.loads(result)
#         assert parsed == {}


# class TestFormatYaml:
#     def test_format_yaml_with_all_types(self) -> None:
#         bakebook = ComplexVarsBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = YamlExportFormatter()
#         result = formatter(data)

#         assert "name: app" in result
#         assert "count: 42" in result
#         assert "tags:" in result
#         assert "- a" in result
#         assert "- b" in result

#     def test_format_yaml_empty_bakebook(self) -> None:
#         class EmptyBakebook(Bakebook):
#             pass

#         bakebook = EmptyBakebook()
#         data = bakebook.model_dump(mode="json")
#         formatter = YamlExportFormatter()
#         result = formatter(data)

#         parsed = yaml.safe_load(result)
#         assert parsed == {}


# class TestExport:
#     def test_export_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
#         bakebook = ComplexVarsBakebook()

#         _export(bakebook, format="sh", output=None)

#         captured = capsys.readouterr()
#         assert "export NAME=app" in strip_ansi(captured.out)

#     def test_export_to_file(self, tmp_path: Path) -> None:
#         bakebook = ComplexVarsBakebook()
#         output_path = tmp_path / "config.sh"

#         _export(bakebook, format="sh", output=output_path)

#         assert output_path.exists()
#         content = output_path.read_text()
#         assert "export NAME=app" in content

#     def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
#         bakebook = ComplexVarsBakebook()
#         output_path = tmp_path / "subdir" / "config.sh"

#         _export(bakebook, format="sh", output=output_path)

#         assert output_path.exists()
#         assert output_path.parent.is_dir()


# class TestExportCli:
#     def test_export_sh_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
#         result = run_cli(
#             command=CMD_BAKEFILE,
#             dir_path=complex_vars_project,
#             args=["export", "--format", "sh"],
#         )

#         assert result.exit_code == 0
#         # Should have actual content
#         assert "export NAME=app" in result.out

#     def test_export_dotenv_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
#         result = run_cli(
#             command=CMD_BAKEFILE,
#             dir_path=complex_vars_project,
#             args=["export", "--format", "dotenv"],
#         )

#         assert result.exit_code == 0
#         # Should have actual content
#         assert "NAME=app" in result.out

#     def test_export_json_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
#         result = run_cli(
#             command=CMD_BAKEFILE,
#             dir_path=complex_vars_project,
#             args=["export", "--format", "json"],
#         )

#         assert result.exit_code == 0
#         # Should be valid JSON with actual data
#         data = orjson.loads(result.out)
#         assert data["name"] == "app"
#         assert data["count"] == 42
#         assert data["tags"] == ["a", "b"]

#     def test_export_to_file(self, complex_vars_project: Path, run_cli: RunCli) -> None:
#         output_path = complex_vars_project / "config.json"

#         result = run_cli(
#             command=CMD_BAKEFILE,
#             dir_path=complex_vars_project,
#             args=["export", "--format", "json", "--output", str(output_path)],
#         )

#         assert result.exit_code == 0
#         assert output_path.exists()
#         data = orjson.loads(output_path.read_text())
#         assert data["name"] == "app"
#         assert data["count"] == 42

#     def test_export_short_option(self, complex_vars_project: Path, run_cli: RunCli) -> None:
#         result = run_cli(
#             command=CMD_BAKEFILE,
#             dir_path=complex_vars_project,
#             args=["export", "-f", "json"],
#         )

#         assert result.exit_code == 0
#         # Should be valid JSON with actual data
#         data = orjson.loads(result.out)
#         assert data["name"] == "app"

#     def test_export_no_bakebook(self, no_bakefile_dir: Path, run_cli: RunCli) -> None:
#         result = run_cli(command=CMD_BAKEFILE, dir_path=no_bakefile_dir, args=["export"])

#         assert result.exit_code == 1
#         assert "Directory not found" in result.err

#     def test_export_empty_bakebook(self, no_bakebook_dir: Path, run_cli: RunCli) -> None:
#         result = run_cli(
#             command=CMD_BAKEFILE, dir_path=no_bakebook_dir, args=["export", "--format", "json"]
#         )

#         assert result.exit_code == 1
#         assert "No 'bakebook' found in" in result.err
