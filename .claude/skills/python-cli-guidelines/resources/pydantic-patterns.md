# Pydantic Patterns

Data validation patterns using Pydantic for bakefile.

## Basic Model

```python
from pydantic import BaseModel, Field

class TaskConfig(BaseModel):
    """Configuration for a single task."""
    name: str = Field(..., min_length=1, description="Task name")
    command: str = Field(..., description="Command to execute")
    description: str | None = Field(None, description="Task description")
    working_dir: str | None = Field(None, description="Working directory")
```

## Validation

```python
from pydantic import field_validator, model_validator

class TaskConfig(BaseModel):
    command: str
    name: str

    @field_validator("name")
    @classmethod
    def name_must_be_kebab_case(cls, v: str) -> str:
        if " " in v or "_" in v:
            raise ValueError("name must be kebab-case")
        return v

    @model_validator(mode="after")
    def validate_command_and_name(self) -> "TaskConfig":
        if "rm -rf" in self.command and self.name != "dangerous":
            raise ValueError("dangerous commands must be named 'dangerous'")
        return self
```

## Default Values

```python
from pathlib import Path

class BakefileConfig(BaseModel):
    """Configuration for entire bakefile."""
    project_name: str
    python_version: str = "3.11"
    working_dir: Path = Field(default_factory=lambda: Path.cwd())
```

## Nested Models

```python
class TaskConfig(BaseModel):
    name: str
    command: str

class BakefileConfig(BaseModel):
    """Configuration with nested tasks."""
    project_name: str
    tasks: list[TaskConfig] = Field(default_factory=list)

    @field_validator("tasks")
    @classmethod
    def task_names_unique(cls, tasks: list[TaskConfig]) -> list[TaskConfig]:
        names = [t.name for t in tasks]
        if len(names) != len(set(names)):
            raise ValueError("task names must be unique")
        return tasks
```

## Parsing from Dict

```python
import yaml

def load_bakefile(path: Path) -> BakefileConfig:
    """Load bakefile.py and parse as Pydantic model."""
    data = yaml.safe_load(path.read_text())
    return BakefileConfig(**data)
```

## Environment Variables

```python
from pydantic import Field

class Config(BaseModel):
    """Configuration with environment variable support."""
    database_url: str = Field(default="sqlite:///db.sqlite3", alias="DATABASE_URL")
    debug: bool = Field(default=False, alias="DEBUG")

    class Config:
        populate_by_name = True
```

## Strict Mode

```python
from pydantic import ConfigDict

class StrictConfig(BaseModel):
    """Configuration with strict validation."""
    name: str
    count: int

    model_config = ConfigDict(
        extra="forbid",  # Disallow extra fields
        str_strip_whitespace=True,
        validate_default=True
    )
```

## Custom Types

```python
from pydantic import BeforeValidator

def parse_command(v: str | list[str]) -> list[str]:
    """Parse command string or list to list of strings."""
    if isinstance(v, str):
        return v.split()
    return v

CommandArgs = list[str]  # Simplified for Python 3.10+

class TaskConfig(BaseModel):
    command: CommandArgs
```

## Serialization

```python
class TaskConfig(BaseModel):
    name: str
    command: str

    def to_dict(self) -> dict:
        """Export to dict."""
        return self.model_dump()

    def to_json(self) -> str:
        """Export to JSON."""
        return self.model_dump_json(indent=2)
```

## Error Handling

```python
from pydantic import ValidationError

try:
    config = BakefileConfig(**data)
except ValidationError as e:
    typer.echo(f"Invalid bakefile.py: {e}", err=True)
    raise typer.Exit(code=1)
```

## Best Practices

1. **Use Field()** - For all attributes with constraints
2. **Provide defaults** - Where sensible
3. **Validate early** - At input boundaries
4. **Custom validators** - For business logic
5. **Type hints** - Always required
6. **Descriptive errors** - Use `Field(description=)`
