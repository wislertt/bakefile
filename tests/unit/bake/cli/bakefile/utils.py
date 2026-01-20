import datetime
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import orjson
from pydantic import (
    BaseModel,
    Field,
    SecretBytes,
    SecretStr,
    TypeAdapter,
    ValidationError,
    create_model,
)

from bake.ui import run
from tests.utils.bakefiles.complex_vars import (
    ComplexVarsBakebook,
    DeepNestedModel,
    NestedModel,
)


# Define test models for BaseModel (nested model) test cases
class Address(BaseModel):
    street: str
    city: str
    zipcode: str


class Person(BaseModel):
    name: str
    age: int
    address: Address


class Company(BaseModel):
    name: str
    employees: list[Person]
    founded: datetime.date


T = TypeVar("T")


class ValueParser(ABC, Generic[T]):
    @abstractmethod
    def __call__(self, value: str) -> T: ...


class BoolParser(ValueParser[bool]):
    def __call__(self, value: str) -> bool:
        try:
            return TypeAdapter(bool).validate_python(value)
        except ValidationError as e:
            raise ValueError(f"invalid value {value!r}") from e


class OptionalStringParser(ValueParser[None | str]):
    def __call__(self, value: str) -> None | str:
        return None if value.strip().lower() in {""} else value


class JsonParser(ValueParser[str]):
    def __call__(self, value: str) -> str:
        return orjson.loads(value)


class NormalizedStringParser(ValueParser[str]):
    """Parser that normalizes line endings (\\r -> \\n) for dotenv compatibility."""

    def __call__(self, value: str) -> str:
        # dotenv_values converts \\r to \\n, so we need to do the same for comparison
        return value.replace("\r", "\n")


class BaseModelParser(ValueParser[BaseModel]):
    def __init__(self, model_type: type[BaseModel]):
        self.model_type = model_type

    def __call__(self, value: str) -> BaseModel:
        return self.model_type.model_validate(orjson.loads(value))


MASKED_SECRET_STRING = "**********"

ALTERNATIVE_MULTI_LINES = """
    This is alternative
    Multi Lines
    """


def get_str_from_inline_env(inline_env: str) -> str:
    parsed = run(
        f'VALUE={inline_env} python -c \'import os; print(os.environ["VALUE"], end="")\'',
        check=False,
    )
    value = parsed.stdout
    return value


def split_export_sh_lines(output: str) -> list[str]:
    return re.split(r"\n(?=export )", output)


ReverseFuncType = ValueParser[Any] | None | type


@dataclass(frozen=True)
class FormatTestCase:
    value: Any
    value_type: type
    expected: str
    reverse_func: ReverseFuncType = None


# Common test cases for shell value formatting
COMMON_FORMAT_SHELL_VALUE_CASES: list[FormatTestCase] = [
    # simple types
    FormatTestCase("simple", str, "simple", None),
    FormatTestCase("with spaces", str, "'with spaces'", None),
    FormatTestCase("", str, "''", None),
    FormatTestCase(42, int, "42", int),
    FormatTestCase(-42, int, "-42", int),
    FormatTestCase(0, int, "0", int),
    FormatTestCase(1.23e-10, float, "1.23e-10", float),
    FormatTestCase(True, bool, "true", BoolParser()),
    FormatTestCase(False, bool, "false", BoolParser()),
    FormatTestCase(None, type(None), "", OptionalStringParser()),
    # special characters
    FormatTestCase('say "hello"', str, "'say \"hello\"'", None),
    FormatTestCase("don't", str, "'don'\"'\"'t'", None),
    FormatTestCase("C:\\Users\\test", str, "'C:\\Users\\test'", None),
    FormatTestCase("PATH=$HOME", str, "'PATH=$HOME'", None),
    FormatTestCase("input | output", str, "'input | output'", None),
    FormatTestCase("cmd; next", str, "'cmd; next'", None),
    FormatTestCase("café naïve", str, "'café naïve'", None),
    FormatTestCase("hello 🌍", str, "'hello 🌍'", None),
    FormatTestCase(" ", str, "' '", None),
    # complex types
    FormatTestCase(
        {"path": "/usr/bin", "query": 'SELECT * FROM "users"', "command": "echo $HOME"},
        dict,
        '\'{"path":"/usr/bin","query":"SELECT * FROM \\"users\\"","command":"echo $HOME"}\'',
        JsonParser(),
    ),
    FormatTestCase("multi-lines\nstring", str, "'multi-lines\nstring'", None),
    # lists
    FormatTestCase([], list, "'[]'", JsonParser()),
    FormatTestCase(["a", "b"], list, '\'["a","b"]\'', JsonParser()),
    FormatTestCase(
        ["item with spaces", "another"], list, '\'["item with spaces","another"]\'', JsonParser()
    ),
    FormatTestCase(
        ['say "hello"', "don't"], list, '\'["say \\"hello\\"","don\'"\'"\'t"]\'', JsonParser()
    ),
    FormatTestCase(["$PATH", "|pipe"], list, '\'["$PATH","|pipe"]\'', JsonParser()),
    FormatTestCase([[1, 2], ["nested"]], list, "'[[1,2],[\"nested\"]]'", JsonParser()),
    # dicts
    FormatTestCase({}, dict, "'{}'", JsonParser()),
    FormatTestCase({"key": "value"}, dict, '\'{"key":"value"}\'', JsonParser()),
    FormatTestCase({"a": {"b": {"c": "deep"}}}, dict, '\'{"a":{"b":{"c":"deep"}}}\'', JsonParser()),
    # Additional multiline cases
    FormatTestCase(
        """
        multi line
        string
        """,
        str,
        """'
        multi line
        string
        '""",
        None,
    ),
    FormatTestCase(
        {
            "path": "/usr/bin",
            "query": 'SELECT * FROM "users"',
            "command": "echo $HOME",
            "multi-lines": "this is\nmulti lines",
            "multi-lines-2": """
                multi line
                string
                """,
        },
        dict,
        '\'{"path":"/usr/bin","query":"SELECT * FROM \\"users\\"","command":"echo $HOME",'
        '"multi-lines":"this is\\nmulti lines",'
        '"multi-lines-2":"\\n                multi line\\n'
        "                string\\n                \"}'",
        JsonParser(),
    ),
    # shell-specific special characters
    FormatTestCase("backtick `", str, "'backtick `'", None),
    FormatTestCase("ampersand &", str, "'ampersand &'", None),
    FormatTestCase("parentheses ()", str, "'parentheses ()'", None),
    FormatTestCase("braces {}", str, "'braces {}'", None),
    FormatTestCase("asterisk *", str, "'asterisk *'", None),
    FormatTestCase("question ?", str, "'question ?'", None),
    FormatTestCase("tilde ~", str, "'tilde ~'", None),
    FormatTestCase("hash #", str, "'hash #'", None),
    FormatTestCase("exclamation !", str, "'exclamation !'", None),
    FormatTestCase("double **", str, "'double **'", None),
    # numeric edge cases
    FormatTestCase(float("inf"), float, "inf", float),
    FormatTestCase(float("-inf"), float, "-inf", float),
    FormatTestCase(0.0, float, "0.0", float),
    FormatTestCase(-0.0, float, "-0.0", float),
    FormatTestCase(3.141592653589793, float, "3.141592653589793", float),
    FormatTestCase(1e308, float, "1e+308", float),
    # string edge cases - escape sequences
    FormatTestCase("tab\there", str, "'tab\there'", None),
    FormatTestCase("carriage\return", str, "'carriage\return'", None),
    FormatTestCase("bell\x07", str, "'bell\x07'", None),
    FormatTestCase("\tmixed\twhitespace\n", str, "'\tmixed\twhitespace\n'", None),
    # string edge cases - whitespace variations
    FormatTestCase("  leading", str, "'  leading'", None),
    FormatTestCase("trailing  ", str, "'trailing  '", None),
    FormatTestCase("  both  ", str, "'  both  '", None),
    FormatTestCase("\t\ttabs\t\t", str, "'\t\ttabs\t\t'", None),
    FormatTestCase(" \t mixed \t ", str, "' \t mixed \t '", None),
    # string edge cases - strings that look like types
    FormatTestCase("123", str, "123", None),
    FormatTestCase("-456", str, "-456", None),
    FormatTestCase("1.23", str, "1.23", None),
    FormatTestCase("true", str, "true", None),
    FormatTestCase("false", str, "false", None),
    FormatTestCase("null", str, "null", None),
    FormatTestCase("[]", str, "'[]'", None),
    FormatTestCase("{}", str, "'{}'", None),
    # complex nesting edge cases
    FormatTestCase(
        {"outer": {"inner": {"deep": {"value": 42}}}},
        dict,
        '\'{"outer":{"inner":{"deep":{"value":42}}}}\'',
        JsonParser(),
    ),
    FormatTestCase(
        {"mixed": [1, "two", {"three": 4}, None]},
        dict,
        '\'{"mixed":[1,"two",{"three":4},null]}\'',
        JsonParser(),
    ),
    FormatTestCase(
        [[[[["deep"]]]]],
        list,
        "'[[[[[\"deep\"]]]]]'",
        JsonParser(),
    ),
    FormatTestCase(
        {
            "list_of_dicts": [{"a": 1}, {"b": 2}],
            "dict_of_lists": {"x": [1, 2], "y": [3, 4]},
        },
        dict,
        '\'{"list_of_dicts":[{"a":1},{"b":2}],"dict_of_lists":{"x":[1,2],"y":[3,4]}}\'',
        JsonParser(),
    ),
]


COMMON_FORMAT_SHELL_VALUE_CASES2: list[FormatTestCase] = [
    # simple types
    FormatTestCase("simple", str, "simple", None),
    FormatTestCase("with spaces", str, '"with spaces"', None),
    FormatTestCase("", str, '""', None),  # Empty string gets quoted as ""
    FormatTestCase(42, int, "42", int),
    FormatTestCase(-42, int, "-42", int),
    FormatTestCase(0, int, "0", int),
    FormatTestCase(1.23e-10, float, "1.23e-10", float),
    FormatTestCase(True, bool, "true", BoolParser()),
    FormatTestCase(False, bool, "false", BoolParser()),
    FormatTestCase(None, type(None), "", OptionalStringParser()),
    # special characters
    # Double quotes only → single quotes
    FormatTestCase('say "hello"', str, "'say \"hello\"'", None),
    # Single quotes only → double quotes
    FormatTestCase("don't", str, '"don\'t"', None),
    # Has special chars → double quotes with escaping
    FormatTestCase("C:\\Users\\test", str, '"C:\\\\Users\\\\test"', None),
    FormatTestCase("PATH=$HOME", str, '"PATH=$HOME"', None),
    FormatTestCase("input | output", str, '"input | output"', None),
    FormatTestCase("cmd; next", str, '"cmd; next"', None),
    # Unicode/special chars → double quotes
    FormatTestCase("café naïve", str, '"café naïve"', None),
    FormatTestCase("hello 🌍", str, '"hello 🌍"', None),
    FormatTestCase(" ", str, '" "', None),
    # complex types - JSON wrapped in double quotes with escaping
    FormatTestCase(
        {"path": "/usr/bin", "query": 'SELECT * FROM "users"', "command": "echo $HOME"},
        dict,
        (
            '"{\\"path\\":\\"/usr/bin\\",\\"query\\":\\"SELECT * FROM \\\\\\"users\\'
            '\\\\"\\",\\"command\\":\\"echo $HOME\\"}"'
        ),
        JsonParser(),
    ),
    FormatTestCase("multi-lines\nstring", str, '"multi-lines\nstring"', None),
    # lists - JSON wrapped in double quotes with escaping
    FormatTestCase([], list, '"[]"', JsonParser()),
    FormatTestCase(["a", "b"], list, '"[\\"a\\",\\"b\\"]"', JsonParser()),
    FormatTestCase(
        ["item with spaces", "another"],
        list,
        '"[\\"item with spaces\\",\\"another\\"]"',
        JsonParser(),
    ),
    FormatTestCase(
        ['say "hello"', "don't"],
        list,
        '"[\\"say \\\\\\"hello\\\\\\"\\",\\"don\'t\\"]"',
        JsonParser(),
    ),
    FormatTestCase(["$PATH", "|pipe"], list, '"[\\"$PATH\\",\\"|pipe\\"]"', JsonParser()),
    FormatTestCase([[1, 2], ["nested"]], list, '"[[1,2],[\\"nested\\"]]"', JsonParser()),
    # dicts - JSON wrapped in double quotes with escaping
    FormatTestCase({}, dict, '"{}"', JsonParser()),
    FormatTestCase({"key": "value"}, dict, '"{\\"key\\":\\"value\\"}"', JsonParser()),
    FormatTestCase(
        {"a": {"b": {"c": "deep"}}},
        dict,
        '"{\\"a\\":{\\"b\\":{\\"c\\":\\"deep\\"}}}"',
        JsonParser(),
    ),
    # Additional multiline cases
    FormatTestCase(
        """
        multi line
        string
        """,
        str,
        '"\n        multi line\n        string\n        "',
        None,
    ),
    FormatTestCase(
        {
            "path": "/usr/bin",
            "query": 'SELECT * FROM "users"',
            "command": "echo $HOME",
            "multi-lines": "this is\nmulti lines",
            "multi-lines-2": """
                multi line
                string
                """,
        },
        dict,
        (
            '"{\\"path\\":\\"/usr/bin\\",\\"query\\":\\"SELECT * FROM \\\\\\"users\\'
            '\\\\"\\",\\"command\\":\\"echo $HOME\\",\\"multi-lines\\":\\"this is\\\\'
            'nmulti lines\\",\\"multi-lines-2\\":\\"\\\\n                multi line\\\\n    '
            '            string\\\\n                \\"}"'
        ),
        JsonParser(),
    ),
    # shell-specific special characters - all need double quotes with escaping
    # Note: reverse_func is None for these because get_str_from_inline_env would
    # shell-evaluate them (e.g., $HOME expands, ` runs command), changing the value
    FormatTestCase("backtick `", str, '"backtick `"', None),
    FormatTestCase("ampersand &", str, '"ampersand &"', None),
    FormatTestCase("parentheses ()", str, '"parentheses ()"', None),
    FormatTestCase("braces {}", str, '"braces {}"', None),
    FormatTestCase("asterisk *", str, '"asterisk *"', None),
    FormatTestCase("question ?", str, '"question ?"', None),
    FormatTestCase("tilde ~", str, '"tilde ~"', None),
    FormatTestCase("hash #", str, '"hash #"', None),
    FormatTestCase("exclamation !", str, '"exclamation !"', None),
    FormatTestCase("double **", str, '"double **"', None),
    # numeric edge cases
    FormatTestCase(float("inf"), float, "inf", float),
    FormatTestCase(float("-inf"), float, "-inf", float),
    FormatTestCase(0.0, float, "0.0", float),
    FormatTestCase(-0.0, float, "-0.0", float),
    FormatTestCase(3.141592653589793, float, "3.141592653589793", float),
    FormatTestCase(1e308, float, "1e+308", float),
    # string edge cases - escape sequences
    FormatTestCase("tab\there", str, '"tab\there"', None),
    FormatTestCase("carriage\return", str, '"carriage\return"', None),  # dotenv converts \r to \n
    FormatTestCase("bell\x07", str, '"bell\x07"', None),
    FormatTestCase("\tmixed\twhitespace\n", str, '"\tmixed\twhitespace\n"', None),
    # string edge cases - whitespace variations
    FormatTestCase("  leading", str, '"  leading"', None),
    FormatTestCase("trailing  ", str, '"trailing  "', None),
    FormatTestCase("  both  ", str, '"  both  "', None),
    FormatTestCase("\t\ttabs\t\t", str, '"\t\ttabs\t\t"', None),
    FormatTestCase(" \t mixed \t ", str, '" \t mixed \t "', None),
    # string edge cases - strings that look like types (alphanumeric, no quotes)
    FormatTestCase("123", str, "123", None),
    FormatTestCase("-456", str, '"-456"', None),  # Has minus, gets quoted
    FormatTestCase("1.23", str, '"1.23"', None),  # Has dot, gets quoted
    FormatTestCase("true", str, "true", None),
    FormatTestCase("false", str, "false", None),
    FormatTestCase("null", str, "null", None),
    # JSON-like strings get quoted
    FormatTestCase("[]", str, '"[]"', None),
    FormatTestCase("{}", str, '"{}"', None),
    # complex nesting edge cases - JSON wrapped in double quotes with escaping
    FormatTestCase(
        {"outer": {"inner": {"deep": {"value": 42}}}},
        dict,
        '"{\\"outer\\":{\\"inner\\":{\\"deep\\":{\\"value\\":42}}}}"',
        JsonParser(),
    ),
    FormatTestCase(
        {"mixed": [1, "two", {"three": 4}, None]},
        dict,
        '"{\\"mixed\\":[1,\\"two\\",{\\"three\\":4},null]}"',
        JsonParser(),
    ),
    FormatTestCase(
        [[[[["deep"]]]]],
        list,
        '"[[[[[\\"deep\\"]]]]]"',
        JsonParser(),
    ),
    FormatTestCase(
        {
            "list_of_dicts": [{"a": 1}, {"b": 2}],
            "dict_of_lists": {"x": [1, 2], "y": [3, 4]},
        },
        dict,
        '"{\\"list_of_dicts\\":[{\\"a\\":1},{\\"b\\":2}],\\"dict_of_lists\\":{\\"x\\":[1,2],\\"y\\":[3,4]}}"',
        JsonParser(),
    ),
]


class AlternateDefaultsComplexVarsBakebook(ComplexVarsBakebook):
    """Test bakebook with DIFFERENT defaults than ComplexVarsBakebook.

    This allows us to verify env vars are actually being read (not just using defaults)
    when we set env to the original ComplexVarsBakebook values.
    """

    # Original fields with different defaults
    name: str = "default_name"
    count: int = 0
    enabled: bool = False
    tags: list = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    nullable: str | None = "not_null"

    # String edge cases with different defaults
    empty_string: str = "not_empty"
    single_space: str = ""
    double_quotes: str = "no quotes"
    single_quotes: str = "dont"
    backslashes: str = "C:/test"
    dollar_sign: str = "NOPATH"
    pipe: str = "input"
    semicolon: str = "cmd"
    unicode: str = "cafe naive"
    emoji: str = "hello world"
    multi_lines: str = "this is alternative\nmulti lines"
    multi_lines_2: str = ALTERNATIVE_MULTI_LINES

    # Numeric edge cases with different defaults
    zero: int = 1
    negative: int = 42
    scientific: float = 9.87e-5

    # List edge cases with different defaults
    empty_list: list = Field(default_factory=lambda: ["not", "empty"])
    list_with_spaces: list = Field(default_factory=lambda: ["nospace"])
    list_with_quotes: list = Field(default_factory=lambda: ["noquotes"])
    list_with_special: list = Field(default_factory=lambda: ["nospecial"])
    nested_list: list = Field(default_factory=lambda: [[99]])

    # Dict edge cases with different defaults
    empty_dict: dict = Field(default_factory=lambda: {"key": "value"})
    nested_dict: dict = Field(default_factory=lambda: {"shallow": "value"})
    dict_with_special_values: dict = Field(default_factory=lambda: {"safe": "value"})
    dict_with_multi_lines: dict = Field(
        default_factory=lambda: {
            "path": "/alt/bin",
            "query": 'SELECT * FROM "alt_users"',
            "command": "echo $ALT_HOME",
            "multi-lines": "this is alternative\nmulti lines",
            "multi-lines-2": ALTERNATIVE_MULTI_LINES,
        }
    )

    # Nested Pydantic models with different defaults
    nested_model: NestedModel = Field(
        default_factory=lambda: NestedModel(value="alt_nested", count=99)
    )
    deep_nested: DeepNestedModel = Field(
        default_factory=lambda: DeepNestedModel(
            name="alt_deep", nested=NestedModel(value="alt_value", count=88)
        )
    )

    # SecretStr with different defaults
    api_key: SecretStr = Field(default_factory=lambda: SecretStr("alternate_secret_key"))
    password: SecretStr = Field(default_factory=lambda: SecretStr("alt_password"))


def _assert_values_differ(value1: Any, value2: Any) -> None:
    # Skip comparison of masked secret values
    if value1 == value2 == MASKED_SECRET_STRING:
        return

    if isinstance(value1, dict) and isinstance(value2, dict):
        # Both are dicts - if they have the same keys, recursively check
        if set(value1.keys()) == set(value2.keys()):
            for key in value1:
                _assert_values_differ(value1[key], value2[key])
        else:
            # Different keys, just check they're not equal
            assert value1 != value2
    else:
        # Not dicts (or only one is dict), just check they differ
        assert value1 != value2


def assert_bakebooks_differ(bakebook1: ComplexVarsBakebook, bakebook2: ComplexVarsBakebook) -> None:
    data1 = bakebook1.model_dump(mode="json")
    data2 = bakebook2.model_dump(mode="json")

    # Assert both have the same keys
    assert set(data1.keys()) == set(data2.keys())

    # Check each field differs
    for key in data1:
        _assert_values_differ(data1[key], data2[key])


def _assert_dict_values_match(
    actual: dict[str, Any], expected: dict[str, Any], context: str = "Values"
) -> None:
    """Assert that dictionary values match expected values.

    Provides detailed error messages showing missing/extra keys and mismatched values.

    Parameters
    ----------
    actual : dict[str, Any]
        The actual dictionary
    expected : dict[str, Any]
        The expected dictionary
    context : str, optional
        Context for the error message, by default "Values"
    """
    if actual == expected:
        return

    actual_keys = set(actual.keys())
    expected_keys = set(expected.keys())

    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    mismatched = [k for k in expected_keys & actual_keys if actual[k] != expected[k]]

    error_parts = [f"{context} do not match expected values:"]
    if missing:
        error_parts.append(f"\n  Missing keys:\n    {sorted(missing)}")
    if extra:
        error_parts.append(f"\n  Extra keys:\n    {sorted(extra)}")
    if mismatched:
        error_parts.append("\n  Mismatched values:")
        for key in sorted(mismatched):
            expected_val = repr(expected[key])
            got_val = repr(actual[key])
            error_parts.append(
                f"\n    {key}:\n      expected: {expected_val}\n      got: {got_val}"
            )

    raise AssertionError("\n".join(error_parts))


def _normalize_dotenv_values(
    parsed: dict[str, str | None], expected: dict[str, Any]
) -> dict[str, Any]:
    """Normalize parsed dotenv values back to their original Python types.

    dotenv_values always returns strings (or None), but the original values may be
    None, bool, int, float, list, dict, etc. This function converts them back.

    Parameters
    ----------
    parsed : dict[str, str | None]
        The parsed dotenv values (always strings from dotenv_values)
    expected : dict[str, Any]
        The expected values dict to infer types from

    Returns
    -------
    dict[str, Any]
        Dictionary with values converted to their original Python types
    """
    parsed_normalized: dict[str, Any] = {}
    for key, value in parsed.items():
        # dotenv_values can return None, skip those
        if value is None:
            continue

        key_lower = key.lower()
        # Get the expected type from the expected dict
        expected_value = expected.get(key_lower)

        # dotenv_values always returns strings, but type checker needs help
        assert isinstance(value, str)

        if value == "" and expected_value is None:
            # Empty string for None field → None
            parsed_normalized[key_lower] = None
        elif value == "true":
            parsed_normalized[key_lower] = True
        elif value == "false":
            parsed_normalized[key_lower] = False
        elif value.startswith(("[", "{")):
            # JSON-serialized list or dict
            parsed_normalized[key_lower] = orjson.loads(value)
        elif isinstance(expected_value, (int, float)):
            # Convert back to number
            parsed_normalized[key_lower] = type(expected_value)(value)
        else:
            # Keep as string (unquote if wrapped in quotes)
            parsed_normalized[key_lower] = value

    return parsed_normalized


def _assert_export_lines_match(
    lines: list[str], expected: list[str], context: str = "Export"
) -> None:
    """Assert that export lines match expected values.

    Provides detailed error messages showing missing/extra exports when they don't match.

    Parameters
    ----------
    lines : list[str]
        The actual export lines
    expected : list[str]
        The expected export lines
    context : str, optional
        Context for the error message, by default "Export"
    """
    lines_set = set(lines)
    expected_set = set(expected)

    if lines_set != expected_set:
        missing = expected_set - lines_set
        extra = lines_set - expected_set

        error_parts = [f"{context} output does not match expected values:"]
        if missing:
            error_parts.append(f"\n  Missing exports:\n    {sorted(missing)}")
        if extra:
            error_parts.append(f"\n  Extra exports:\n    {sorted(extra)}")
        if len(lines) != len(expected):
            error_parts.append(f"\n  Count mismatch: got {len(lines)}, expected {len(expected)}")

        raise AssertionError("\n".join(error_parts))


def _assert_pydantic_can_consume(
    env_value: str,
    expected_value: Any,
    value_type: type,
    value_model: type[BaseModel] | None = None,
) -> None:
    """Validate that a shell-parsed string can be consumed by Pydantic.

    This simulates reading from os.environ and validates that Pydantic can
    parse the string back to the expected value.

    Parameters
    ----------
    env_value : str
        The string after shell parsing (simulates os.environ value)
    expected_value : Any
        The expected value after parsing
    value_type : type
        The Pydantic field type
    value_model : type[BaseModel] | None, optional
        Optional pre-created model for testing primitive types, by default None
    """
    if value_type is type(None):
        # Known limitation: None exports as empty string, can't round-trip
        assert env_value == ""
    elif isinstance(value_type, type) and issubclass(value_type, BaseModel):
        # BaseModel: JSON-serialized, use model_validate_json
        parsed_model = value_type.model_validate_json(env_value)
        assert parsed_model.model_dump(mode="json") == expected_value.model_dump(mode="json")
    elif value_type in (list, dict):
        # list/dict: JSON-serialized strings, use TypeAdapter.validate_json
        parsed_value = TypeAdapter(value_type).validate_json(env_value)
        assert parsed_value == expected_value
    else:
        # All other types: pass string directly to model (Pydantic handles coercion)
        # Create model lazily if not provided
        model = value_model or create_model("ValueModel", value=(value_type, ...))
        parsed_model = model(value=env_value)
        if value_type not in (SecretStr, SecretBytes):
            # Use model_dump() to extract value (type-safe for any BaseModel with 'value' field)
            assert parsed_model.model_dump()["value"] == expected_value


def _assert_export_roundtrip(
    exported_data: dict[str, Any],
    format_name: str = "export",
) -> None:
    """Assert that exported data can be loaded back into a bakebook.

    Verifies that:
    1. The exported data matches ComplexVarsBakebook defaults
    2. AlternateDefaultsComplexVarsBakebook can be constructed from the exported data
    3. The constructed bakebook matches ComplexVarsBakebook defaults

    Parameters
    ----------
    exported_data : dict[str, Any]
        The exported data (from JSON, YAML, etc.)
    format_name : str, optional
        The format name for error messages, by default "export"
    """
    # Compare exported with expected
    expected = ComplexVarsBakebook().model_dump(mode="json")
    _assert_dict_values_match(exported_data, expected, context=f"{format_name} export")

    # Verify that AlternateDefaultsComplexVarsBakebook can be constructed from exported data
    # and will have the same values as ComplexVarsBakebook
    alt_from_export = AlternateDefaultsComplexVarsBakebook.model_validate(exported_data)
    default_complex_vars_bb = ComplexVarsBakebook()
    _assert_dict_values_match(
        alt_from_export.model_dump(mode="json"),
        default_complex_vars_bb.model_dump(mode="json"),
        context=f"{format_name}-loaded bakebook",
    )
