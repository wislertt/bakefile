from pydantic import BaseModel, Field, SecretStr

from bake import Bakebook


class NestedModel(BaseModel):
    """A nested Pydantic model for testing export."""

    value: str = "nested_value"
    count: int = 10


class DeepNestedModel(BaseModel):
    """A deeply nested Pydantic model for testing export."""

    name: str = "deep"
    nested: NestedModel = Field(default_factory=NestedModel)


MULTI_LINES = """
    This is
    Multi Lines
    """


class ComplexVarsBakebook(Bakebook):
    # Original fields (keep for backwards compatibility)
    name: str = "app"
    count: int = 42
    enabled: bool = True
    tags: list = Field(default_factory=lambda: ["a", "b"])
    config: dict = Field(default_factory=lambda: {"key": "value"})
    nullable: str | None = None

    # String edge cases
    empty_string: str = ""
    single_space: str = " "
    double_quotes: str = 'say "hello"'
    single_quotes: str = "don't"
    backslashes: str = "C:\\Users\\test"
    dollar_sign: str = "PATH=$HOME"
    pipe: str = "input | output"
    semicolon: str = "cmd; next"
    unicode: str = "café naïve"
    emoji: str = "hello 🌍"
    multi_lines: str = "this is\nmulti lines"
    multi_lines_2: str = MULTI_LINES

    # Numeric edge cases
    zero: int = 0
    negative: int = -42
    scientific: float = 1.23e-10

    # List edge cases
    empty_list: list = Field(default_factory=list)
    list_with_spaces: list = Field(default_factory=lambda: ["item with spaces", "another"])
    list_with_quotes: list = Field(default_factory=lambda: ['say "hello"', "don't"])
    list_with_special: list = Field(default_factory=lambda: ["$PATH", "|pipe"])
    nested_list: list = Field(default_factory=lambda: [[1, 2], ["nested"]])

    # Dict edge cases
    empty_dict: dict = Field(default_factory=dict)
    nested_dict: dict = Field(default_factory=lambda: {"a": {"b": {"c": "deep"}}})
    dict_with_special_values: dict = Field(
        default_factory=lambda: {
            "path": "/usr/bin",
            "query": 'SELECT * FROM "users"',
            "command": "echo $HOME",
        }
    )
    dict_with_multi_lines: dict = Field(
        default_factory=lambda: {
            "path": "/usr/bin",
            "query": 'SELECT * FROM "users"',
            "command": "echo $HOME",
            "multi-lines": "this is\nmulti lines",
            "multi-lines-2": MULTI_LINES,
        }
    )

    # Nested Pydantic models
    nested_model: NestedModel = Field(default_factory=NestedModel)
    deep_nested: DeepNestedModel = Field(default_factory=DeepNestedModel)

    # SecretStr - should be masked in export
    api_key: SecretStr = Field(default_factory=lambda: SecretStr("super_secret_key_123"))
    password: SecretStr = Field(default_factory=lambda: SecretStr("my_password"))


bakebook = ComplexVarsBakebook()
