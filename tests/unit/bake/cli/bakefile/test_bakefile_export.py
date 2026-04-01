import datetime
import decimal
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml
from dotenv import dotenv_values
from pandas import Timedelta
from pydantic import HttpUrl, PastDate, SecretBytes, SecretStr, create_model

from bake.cli.bakefile.export import (
    ExportFormatter,
    _export,
    _format_dotenv_value,
    _format_shell_value,
)
from bake.ui import run
from bake.utils.constants import CMD_BAKEFILE
from tests.conftest import RunCli
from tests.unit.bake.cli.bakefile.utils import (
    COMMON_FORMAT_SHELL_VALUE_CASES,
    COMMON_FORMAT_SHELL_VALUE_CASES2,
    MASKED_SECRET_STRING,
    Address,
    AlternateDefaultsComplexVarsBakebook,
    BaseModelParser,
    Company,
    Person,
    ReverseFuncType,
    _assert_dict_values_match,
    _assert_export_lines_match,
    _assert_export_roundtrip,
    _assert_pydantic_can_consume,
    _normalize_dotenv_values,
    assert_bakebooks_differ,
    get_str_from_inline_env,
    split_export_sh_lines,
)
from tests.utils.bakefiles.complex_vars import (
    ComplexVarsBakebook,
)
from tests.utils.misc import flaky_on_macos_ci


class TestExportCli:
    def test_export_sh_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "sh"],
        ).stripped()

        # Assert export output succeeds and has expected structure
        assert result.exit_code == 0
        lines = split_export_sh_lines(result.out.strip())

        # Verify all lines start with "export "
        bad_lines = [line for line in lines if not line.startswith("export ")]
        assert not bad_lines, f"Some lines don't start with 'export ': {bad_lines}"

        expected = [
            "export NAME=app",
            "export COUNT=42",
            "export ENABLED=true",
            'export TAGS=\'["a","b"]\'',
            'export CONFIG=\'{"key":"value"}\'',
            "export NULLABLE=",
            "export EMPTY_STRING=''",
            "export SINGLE_SPACE=' '",
            "export DOUBLE_QUOTES='say \"hello\"'",
            "export SINGLE_QUOTES='don'\"'\"'t'",
            "export BACKSLASHES='C:\\Users\\test'",
            "export DOLLAR_SIGN='PATH=$HOME'",
            "export PIPE='input | output'",
            "export SEMICOLON='cmd; next'",
            "export UNICODE='café naïve'",
            "export EMOJI='hello 🌍'",
            "export MULTI_LINES='this is\nmulti lines'",
            "export MULTI_LINES_2='\n    This is\n    Multi Lines\n    '",
            "export ZERO=0",
            "export NEGATIVE=-42",
            "export SCIENTIFIC=1.23e-10",
            "export EMPTY_LIST='[]'",
            'export LIST_WITH_SPACES=\'["item with spaces","another"]\'',
            'export LIST_WITH_QUOTES=\'["say \\"hello\\"","don\'"\'"\'t"]\'',
            'export LIST_WITH_SPECIAL=\'["$PATH","|pipe"]\'',
            "export NESTED_LIST='[[1,2],[\"nested\"]]'",
            "export EMPTY_DICT='{}'",
            'export NESTED_DICT=\'{"a":{"b":{"c":"deep"}}}\'',
            'export DICT_WITH_SPECIAL_VALUES=\'{"path":"/usr/bin",'
            '"query":"SELECT * FROM \\"users\\"","command":"echo $HOME"}\'',
            'export DICT_WITH_MULTI_LINES=\'{"path":"/usr/bin",'
            '"query":"SELECT * FROM \\"users\\"","command":"echo $HOME",'
            '"multi-lines":"this is\\nmulti lines",'
            '"multi-lines-2":"\\n    This is\\n    Multi Lines\\n    "}\'',
            'export NESTED_MODEL=\'{"value":"nested_value","count":10}\'',
            'export DEEP_NESTED=\'{"name":"deep","nested":{"value":"nested_value","count":10}}\'',
            "export API_KEY='**********'",
            "export PASSWORD='**********'",
        ]

        _assert_export_lines_match(lines, expected, context="Export")

    @flaky_on_macos_ci()
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Unix shell command parsing not available on Windows",
    )
    def test_export_sh_env_assignment(
        self, complex_vars_project: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "sh"],
        ).stripped()

        assert result.exit_code == 0
        output = result.out.strip()
        default_complex_vars_bb = ComplexVarsBakebook()
        default_alt_complex_vars_bb = AlternateDefaultsComplexVarsBakebook()
        assert_bakebooks_differ(default_complex_vars_bb, default_alt_complex_vars_bb)

        export_statements = split_export_sh_lines(output)

        # Parse each export statement and set environment variables
        # This simulates: eval "$(bakefile export)" which sets the vars in the shell
        for statement in export_statements:
            env_line = statement.replace("export ", "", 1)
            parts = env_line.split("=", 1)
            assert len(parts) == 2
            key: str = parts[0]
            value: str = parts[1]
            parsed_value = get_str_from_inline_env(inline_env=value)
            monkeypatch.setenv(key, parsed_value)

        # Verify alt_bakebook picks up exported values instead of using its defaults
        alt_env_loaded_bb = AlternateDefaultsComplexVarsBakebook()
        alt_env_loaded_data = alt_env_loaded_bb.model_dump(mode="json")
        default_complex_vars_data = default_complex_vars_bb.model_dump(mode="json")

        # Shell limitation: 'export nullable=' becomes "" instead of None
        # Normalize to None for comparison
        assert alt_env_loaded_data["nullable"] == ""
        alt_env_loaded_data["nullable"] = None
        assert alt_env_loaded_data == default_complex_vars_data

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Unix shell eval (eval, cat) not available on Windows",
    )
    def test_export_sh_eval(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        """Test that exported edge case values work correctly with shell eval."""
        tmp_sh_path = complex_vars_project / "tmp_eval.sh"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "sh", "--output", str(tmp_sh_path)],
        ).stripped()

        assert result.exit_code == 0

        fields = ComplexVarsBakebook().model_dump(mode="json").keys()

        results = []

        for field in fields:
            upper_field = field.upper()
            cmd = f'eval "$(cat {tmp_sh_path})"; echo "{upper_field}=${{{upper_field}}}"'
            completed = run(cmd, shell=True, capture_output=True)
            assert completed.returncode == 0
            results.append(completed.stdout.strip())

        expected = [
            "NAME=app",
            "COUNT=42",
            "ENABLED=true",
            'TAGS=["a","b"]',
            'CONFIG={"key":"value"}',
            "NULLABLE=",
            "EMPTY_STRING=",
            "SINGLE_SPACE=",
            'DOUBLE_QUOTES=say "hello"',
            "SINGLE_QUOTES=don't",
            "BACKSLASHES=C:\\Users\test",
            "DOLLAR_SIGN=PATH=$HOME",
            "PIPE=input | output",
            "SEMICOLON=cmd; next",
            "UNICODE=café naïve",
            "EMOJI=hello 🌍",
            "MULTI_LINES=this is\nmulti lines",
            "MULTI_LINES_2=\n    This is\n    Multi Lines",
            "ZERO=0",
            "NEGATIVE=-42",
            "SCIENTIFIC=1.23e-10",
            "EMPTY_LIST=[]",
            'LIST_WITH_SPACES=["item with spaces","another"]',
            'LIST_WITH_QUOTES=["say \\"hello\\"","don\'t"]',
            'LIST_WITH_SPECIAL=["$PATH","|pipe"]',
            'NESTED_LIST=[[1,2],["nested"]]',
            "EMPTY_DICT={}",
            'NESTED_DICT={"a":{"b":{"c":"deep"}}}',
            'DICT_WITH_SPECIAL_VALUES={"path":"/usr/bin",'
            '"query":"SELECT * FROM \\"users\\"","command":"echo $HOME"}',
            'DICT_WITH_MULTI_LINES={"path":"/usr/bin",'
            '"query":"SELECT * FROM \\"users\\"","command":"echo $HOME",'
            '"multi-lines":"this is\nmulti lines",'
            '"multi-lines-2":"\n    This is\n    Multi Lines\n    "}',
            'NESTED_MODEL={"value":"nested_value","count":10}',
            'DEEP_NESTED={"name":"deep","nested":{"value":"nested_value","count":10}}',
            "API_KEY=**********",
            "PASSWORD=**********",
        ]

        _assert_export_lines_match(results, expected, context="Export")

    def test_export_dotenv_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        # Write to temp file and parse with dotenv to handle multi-line values
        tmp_dotenv_path = complex_vars_project / "tmp_export.env"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "dotenv", "--output", str(tmp_dotenv_path)],
        ).stripped()

        # Assert export output succeeds
        assert result.exit_code == 0

        parsed = dotenv_values(tmp_dotenv_path)

        # Create expected values from ComplexVarsBakebook defaults
        expected = ComplexVarsBakebook().model_dump(mode="json")

        # Convert parsed dotenv values back to their original types
        # so they can be compared directly with expected from model_dump(mode="json")
        parsed_normalized = _normalize_dotenv_values(parsed, expected)

        # Compare parsed and expected
        _assert_dict_values_match(parsed_normalized, expected, context="Dotenv export")

    def test_export_dotenv_env_assignment(
        self, complex_vars_project: Path, run_cli: RunCli, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that dotenv export can be loaded back via environment variables."""
        # Verify defaults are different
        default_complex_vars_bb = ComplexVarsBakebook()
        default_alt_complex_vars_bb = AlternateDefaultsComplexVarsBakebook()
        assert_bakebooks_differ(default_complex_vars_bb, default_alt_complex_vars_bb)

        # Write to temp file and parse with dotenv
        tmp_dotenv_path = complex_vars_project / "tmp_export.env"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "dotenv", "--output", str(tmp_dotenv_path)],
        ).stripped()

        assert result.exit_code == 0
        parsed_env = dotenv_values(tmp_dotenv_path)

        # Set environment variables from parsed dotenv
        # This simulates: loading .env file which sets vars in the environment
        for key, value in parsed_env.items():
            # dotenv_values returns dict[str, str | None], filter out None
            if value is not None:
                monkeypatch.setenv(key, value)

        # Verify alt_bakebook picks up exported values instead of using its defaults
        alt_env_loaded_bb = AlternateDefaultsComplexVarsBakebook()
        alt_env_loaded_data = alt_env_loaded_bb.model_dump(mode="json")
        default_complex_vars_data = default_complex_vars_bb.model_dump(mode="json")

        # Dotenv limitation: empty string values from dotenv become "" instead of None
        # Normalize to None for comparison where applicable
        assert alt_env_loaded_data["nullable"] == ""
        alt_env_loaded_data["nullable"] = None
        assert alt_env_loaded_data == default_complex_vars_data

    def test_export_json_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "json"],
        ).stripped()

        # Assert export output succeeds
        assert result.exit_code == 0

        # Parse JSON output
        exported_data = json.loads(result.out)
        _assert_export_roundtrip(exported_data, format_name="JSON")

    def test_export_json_with_output(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        tmp_json_path = complex_vars_project / "tmp_export.json"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "json", "--output", str(tmp_json_path)],
        ).stripped()

        # Assert export output succeeds
        assert result.exit_code == 0

        # Read and parse JSON from file
        exported_data = json.loads(tmp_json_path.read_text(encoding="utf-8"))
        _assert_export_roundtrip(exported_data, format_name="JSON")

    def test_export_yaml_format(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "yaml"],
        ).stripped()

        # Assert export output succeeds
        assert result.exit_code == 0

        # Parse YAML output
        exported_data = yaml.safe_load(result.out)
        _assert_export_roundtrip(exported_data, format_name="YAML")

    def test_export_yaml_with_output(self, complex_vars_project: Path, run_cli: RunCli) -> None:
        tmp_yaml_path = complex_vars_project / "tmp_export.yaml"
        result = run_cli(
            command=CMD_BAKEFILE,
            dir_path=complex_vars_project,
            args=["export", "--format", "yaml", "--output", str(tmp_yaml_path)],
        ).stripped()

        # Assert export output succeeds
        assert result.exit_code == 0

        # Read and parse YAML from file
        exported_data = yaml.safe_load(tmp_yaml_path.read_text(encoding="utf-8"))
        _assert_export_roundtrip(exported_data, format_name="YAML")


class TestExportFormatter:
    def test_base_formatter_raises_not_implemented(self) -> None:
        """Test that ExportFormatter base class raises NotImplementedError."""
        formatter = ExportFormatter()
        with pytest.raises(NotImplementedError):
            formatter({"key": "value"})

    def test_export_with_unknown_format_raises_value_error(self) -> None:
        """Test that _export raises ValueError for unknown format."""
        bakebook = ComplexVarsBakebook()
        with pytest.raises(ValueError, match="Unknown format: invalid"):
            _export(bakebook=bakebook, format="invalid", output=None)  # ty: ignore[invalid-argument-type]

    def test_export_cli_raises_runtime_error_when_bakebook_not_found(self) -> None:
        """Test that export raises RuntimeError when bakebook is not found."""
        from unittest.mock import MagicMock

        # Mock context with None bakebook that stays None after get_bakebook
        mock_ctx = MagicMock()
        mock_ctx.obj.bakebook = None
        mock_ctx.obj.get_bakebook = MagicMock()  # Does nothing, bakebook stays None

        # Import and call the export function directly
        from bake.cli.bakefile.export import export as export_cmd

        with pytest.raises(RuntimeError, match="Bakebook not found"):
            export_cmd(mock_ctx, format="json")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix shell command parsing not available on Windows",
)
class TestFormatShellValueUnit:
    @pytest.mark.parametrize(
        "value,expected,reverse_func",
        # Extract (value, expected, reverse_func) from common cases, skipping type
        [
            (case.value, case.expected, case.reverse_func)
            for case in COMMON_FORMAT_SHELL_VALUE_CASES
        ],
    )
    def test_format_shell_value(
        self, value: Any, expected: str, reverse_func: ReverseFuncType
    ) -> None:
        result = _format_shell_value(value)
        assert result == expected
        parsed_result = get_str_from_inline_env(result)
        reversed_value = reverse_func(parsed_result) if reverse_func else parsed_result
        assert reversed_value == value

    @pytest.mark.parametrize(
        "value,value_type,expected,reverse_func",
        # Common cases + SecretStr specific case
        [
            (case.value, case.value_type, case.expected, case.reverse_func)
            for case in COMMON_FORMAT_SHELL_VALUE_CASES
        ]
        + [
            # Pydantic-specific types that need model_dump(mode="json") conversion
            # Secret types - masked, no round-trip possible
            (SecretStr("my_secret"), SecretStr, f"'{MASKED_SECRET_STRING}'", None),
            (SecretBytes(b"my_bytes_secret"), SecretBytes, f"'{MASKED_SECRET_STRING}'", None),
            # HttpUrl - becomes plain string
            (HttpUrl("https://example.com/path"), HttpUrl, "https://example.com/path", HttpUrl),
            # PastDate - becomes ISO date string
            (
                datetime.date(2020, 1, 1),
                PastDate,
                "2020-01-01",
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date(),
            ),
            # datetime - becomes ISO datetime string (Z for UTC)
            (
                datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=datetime.timezone.utc),
                datetime.datetime,
                "2024-01-15T10:30:45Z",
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=datetime.timezone.utc
                ),
            ),
            # date - becomes ISO date string
            (
                datetime.date(2024, 12, 25),
                datetime.date,
                "2024-12-25",
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date(),
            ),
            # time - becomes ISO time string
            (
                datetime.time(14, 30, 45),
                datetime.time,
                "14:30:45",
                lambda x: datetime.datetime.strptime(x, "%H:%M:%S").time(),
            ),
            # timedelta - becomes ISO 8601 duration format
            (
                datetime.timedelta(hours=2, seconds=90),
                datetime.timedelta,
                "PT2H1M30S",
                lambda x: Timedelta(x).to_pytimedelta(),
            ),
            # Decimal - becomes float/int in JSON
            (
                decimal.Decimal("123.45"),
                decimal.Decimal,
                "123.45",
                lambda x: decimal.Decimal(x),
            ),
            (decimal.Decimal("42"), decimal.Decimal, "42", lambda x: decimal.Decimal(x)),
            # UUID - becomes string
            (
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                uuid.UUID,
                "12345678-1234-5678-1234-567812345678",
                lambda x: uuid.UUID(x),
            ),
            # Path - becomes string
            (Path("/usr/local/bin"), Path, "/usr/local/bin", lambda x: Path(x)),
            # Pydantic Basemodel
            # Simple BaseModel - becomes dict
            (
                Address(street="123 Main St", city="Springfield", zipcode="12345"),
                Address,
                '\'{"street":"123 Main St","city":"Springfield","zipcode":"12345"}\'',
                BaseModelParser(Address),
                # lambda x: Address.model_validate(orjson.loads(x)),
            ),
            # Nested BaseModel - Person with Address
            (
                Person(
                    name="John Doe",
                    age=30,
                    address=Address(street="456 Oak Ave", city="Shelbyville", zipcode="67890"),
                ),
                Person,
                '\'{"name":"John Doe","age":30,"address":{"street":"456 Oak Ave",'
                '"city":"Shelbyville","zipcode":"67890"}}\'',
                BaseModelParser(Person),
            ),
            # BaseModel with list of BaseModel - Company with list of Person
            (
                Company(
                    name="Acme Corp",
                    employees=[
                        Person(
                            name="Alice",
                            age=28,
                            address=Address(
                                street="111 First St", city="Metropolis", zipcode="11111"
                            ),
                        ),
                        Person(
                            name="Bob",
                            age=35,
                            address=Address(street="222 Second St", city="Gotham", zipcode="22222"),
                        ),
                    ],
                    founded=datetime.date(2020, 1, 1),
                ),
                Company,
                '\'{"name":"Acme Corp",'
                '"employees":['
                '{"name":"Alice","age":28,'
                '"address":{"street":"111 First St","city":"Metropolis","zipcode":"11111"}},'
                '{"name":"Bob","age":35,'
                '"address":{"street":"222 Second St","city":"Gotham","zipcode":"22222"}}'
                "],"
                '"founded":"2020-01-01"}\'',
                BaseModelParser(Company),
            ),
        ],
    )
    def test_format_shell_value_with_model(
        self, value: Any, value_type: type, expected: str, reverse_func: ReverseFuncType
    ) -> None:
        value_model = create_model(
            "ValueModel",
            value=(value_type, ...),
        )

        model = value_model(value=value)
        json_output = model.model_dump(mode="json")

        result = _format_shell_value(json_output["value"])
        assert result == expected
        parsed_result = get_str_from_inline_env(result)
        reversed_value = reverse_func(parsed_result) if reverse_func else parsed_result

        if value_type in (SecretStr, SecretBytes):
            # SecretStr and SecretBytes cannot round-trip (intentionally masked)
            # verify the value was masked
            assert reversed_value == MASKED_SECRET_STRING
        else:
            assert reversed_value == value

        # Validate that env_value can be consumed by Pydantic (simulating os.environ read)
        _assert_pydantic_can_consume(
            env_value=parsed_result,
            expected_value=value,
            value_type=value_type,
            value_model=value_model,
        )

    @pytest.mark.parametrize(
        "value",
        [
            b"hello",
            (1, 2, 3),
            {1, 2, 3},
            frozenset([1, 2, 3]),
            bytearray(b"hello"),
            3.14j,
            object(),
        ],
    )
    def test_format_shell_value_unexpected_type_raises(self, value: Any) -> None:
        with pytest.raises(TypeError, match="Unexpected type for shell export"):
            _format_shell_value(value)


class TestFormatDotEnvValueUnit:
    @pytest.mark.parametrize(
        "value,expected,reverse_func",
        # Extract (value, expected, reverse_func) from common cases, skipping type
        [
            (case.value, case.expected, case.reverse_func)
            for case in COMMON_FORMAT_SHELL_VALUE_CASES2
        ],
    )
    def test_format_dotenv_value(
        self, value: Any, expected: str, reverse_func: ReverseFuncType, tmp_path: Path
    ) -> None:
        result = _format_dotenv_value(value)
        assert result == expected

        # Write to temp file for dotenv_values to parse
        dotenv_file = tmp_path / "test.env"
        dotenv_file.write_text(f"VALUE={result}", encoding="utf-8")
        parsed_dict = dotenv_values(dotenv_file)

        # Extract the parsed value from the dict
        parsed_result = parsed_dict["VALUE"]
        assert isinstance(parsed_result, str)

        reversed_value = reverse_func(parsed_result) if reverse_func else parsed_result

        if not isinstance(value, str) or value not in {"carriage\return"}:
            assert reversed_value == value
        else:
            # NOTE: dotenv normalizes \r to \n during parsing
            assert isinstance(reversed_value, str)
            assert reversed_value.replace("\r", "\n") == "carriage\neturn"

    @pytest.mark.parametrize(
        "value,value_type,expected,reverse_func",
        # Common cases + SecretStr specific case
        [
            (case.value, case.value_type, case.expected, case.reverse_func)
            for case in COMMON_FORMAT_SHELL_VALUE_CASES2
        ]
        + [
            # Pydantic-specific types that need model_dump(mode="json") conversion
            # Secret types - masked, no round-trip possible
            (SecretStr("my_secret"), SecretStr, f'"{MASKED_SECRET_STRING}"', None),
            (SecretBytes(b"my_bytes_secret"), SecretBytes, f'"{MASKED_SECRET_STRING}"', None),
            # HttpUrl - becomes plain string (with quotes for dotenv format)
            (HttpUrl("https://example.com/path"), HttpUrl, '"https://example.com/path"', HttpUrl),
            # PastDate - becomes ISO date string (quoted in dotenv)
            (
                datetime.date(2020, 1, 1),
                PastDate,
                '"2020-01-01"',
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date(),
            ),
            # datetime - becomes ISO datetime string (Z for UTC, quoted in dotenv)
            (
                datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=datetime.timezone.utc),
                datetime.datetime,
                '"2024-01-15T10:30:45Z"',
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=datetime.timezone.utc
                ),
            ),
            # date - becomes ISO date string (quoted in dotenv)
            (
                datetime.date(2024, 12, 25),
                datetime.date,
                '"2024-12-25"',
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date(),
            ),
            # time - becomes ISO time string (quoted in dotenv)
            (
                datetime.time(14, 30, 45),
                datetime.time,
                '"14:30:45"',
                lambda x: datetime.datetime.strptime(x, "%H:%M:%S").time(),
            ),
            # timedelta - becomes ISO 8601 duration format (alphanumeric, no quotes needed)
            (
                datetime.timedelta(hours=2, seconds=90),
                datetime.timedelta,
                "PT2H1M30S",
                lambda x: Timedelta(x).to_pytimedelta(),
            ),
            # Decimal - becomes float/int in JSON (quoted in dotenv for decimals with dots)
            (
                decimal.Decimal("123.45"),
                decimal.Decimal,
                '"123.45"',
                lambda x: decimal.Decimal(x),
            ),
            # Decimal int - becomes int in JSON (numeric, no quotes needed)
            (decimal.Decimal("42"), decimal.Decimal, "42", lambda x: decimal.Decimal(x)),
            # UUID - becomes string (quoted in dotenv)
            (
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                uuid.UUID,
                '"12345678-1234-5678-1234-567812345678"',
                lambda x: uuid.UUID(x),
            ),
            # Path - becomes string (quoted in dotenv for paths with slashes)
            (Path("/usr/local/bin"), Path, '"/usr/local/bin"', lambda x: Path(x)),
            # Pydantic BaseModel
            # Simple BaseModel - becomes dict
            (
                Address(street="123 Main St", city="Springfield", zipcode="12345"),
                Address,
                '"{\\"street\\":\\"123 Main St\\",\\"city\\":\\"Springfield\\",'
                '\\"zipcode\\":\\"12345\\"}"',
                BaseModelParser(Address),
            ),
            # Nested BaseModel - Person with Address
            (
                Person(
                    name="John Doe",
                    age=30,
                    address=Address(street="456 Oak Ave", city="Shelbyville", zipcode="67890"),
                ),
                Person,
                '"{\\"name\\":\\"John Doe\\",\\"age\\":30,'
                '\\"address\\":{\\"street\\":\\"456 Oak Ave\\",'
                '\\"city\\":\\"Shelbyville\\",\\"zipcode\\":\\"67890\\"}}"',
                BaseModelParser(Person),
            ),
            # BaseModel with list of BaseModel - Company with list of Person
            (
                Company(
                    name="Acme Corp",
                    employees=[
                        Person(
                            name="Alice",
                            age=28,
                            address=Address(
                                street="111 First St", city="Metropolis", zipcode="11111"
                            ),
                        ),
                        Person(
                            name="Bob",
                            age=35,
                            address=Address(street="222 Second St", city="Gotham", zipcode="22222"),
                        ),
                    ],
                    founded=datetime.date(2020, 1, 1),
                ),
                Company,
                '"{\\"name\\":\\"Acme Corp\\",\\"employees\\":['
                '{\\"name\\":\\"Alice\\",\\"age\\":28,'
                '\\"address\\":{\\"street\\":\\"111 First St\\",'
                '\\"city\\":\\"Metropolis\\",\\"zipcode\\":\\"11111\\"}},'
                '{\\"name\\":\\"Bob\\",\\"age\\":35,'
                '\\"address\\":{\\"street\\":\\"222 Second St\\",'
                '\\"city\\":\\"Gotham\\",\\"zipcode\\":\\"22222\\"}}],'
                '\\"founded\\":\\"2020-01-01\\"}"',
                BaseModelParser(Company),
            ),
        ],
    )
    def test_format_dotenv_value_with_model(
        self,
        value: Any,
        value_type: type,
        expected: str,
        reverse_func: ReverseFuncType,
        tmp_path: Path,
    ) -> None:
        # Skip Path test on Windows due to path separator differences
        if sys.platform == "win32" and value_type is Path:
            pytest.skip("Path serialization uses backslashes on Windows")

        value_model = create_model(
            "ValueModel",
            value=(value_type, ...),
        )

        model = value_model(value=value)
        json_output = model.model_dump(mode="json")

        result = _format_dotenv_value(json_output["value"])
        assert result == expected

        # Write to temp file for dotenv_values to parse
        dotenv_file = tmp_path / "test.env"
        dotenv_file.write_text(f"VALUE={result}", encoding="utf-8")
        parsed_dict = dotenv_values(dotenv_file)

        # Extract the parsed value from the dict (dotenv_values returns str | None)
        parsed_result = parsed_dict["VALUE"]
        assert parsed_result is not None, "dotenv_values should not return None for VALUE"

        if value_type in (SecretStr, SecretBytes):
            # SecretStr and SecretBytes cannot round-trip (intentionally masked)
            # verify the value was masked
            assert parsed_result == MASKED_SECRET_STRING
        elif value_type is type(None):
            # None exports as empty string
            assert parsed_result == ""
        elif isinstance(value, str) and value == "carriage\return":
            # NOTE: dotenv normalizes \r to \n during parsing
            assert isinstance(parsed_result, str)
            assert parsed_result.replace("\r", "\n") == "carriage\neturn"
        else:
            reversed_value = reverse_func(parsed_result) if reverse_func else parsed_result
            assert reversed_value == value

        # Validate that env_value can be consumed by Pydantic (simulating os.environ read)
        # Skip for carriage\return (dotenv normalizes \r to \n)
        if not (isinstance(value, str) and value == "carriage\return"):
            _assert_pydantic_can_consume(
                env_value=parsed_result,
                expected_value=value,
                value_type=value_type,
                value_model=value_model,
            )

    @pytest.mark.parametrize(
        "value",
        [
            b"hello",
            (1, 2, 3),
            {1, 2, 3},
            frozenset([1, 2, 3]),
            bytearray(b"hello"),
            3.14j,
            object(),
        ],
    )
    def test_format_dotenv_value_unexpected_type_raises(self, value: Any) -> None:
        with pytest.raises(TypeError, match="Unexpected type for dotenv export"):
            _format_dotenv_value(value)
