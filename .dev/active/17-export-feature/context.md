# Export Feature - Context

Last Updated: 2026-01-17

## SESSION PROGRESS (2026-01-17)

### ✅ COMPLETED

- Dev docs structure created
- Plan document finalized with 6 phases
- Codebase explored and understood

### 🟡 IN PROGRESS

- Initial discussion and design complete
- Ready to start implementation

### ⏳ NOT STARTED

- Phase 1: Core Export Logic
- Phase 2: Format Implementations
- Phase 3: CLI Integration
- Phase 4: Error Handling
- Phase 5: Testing
- Phase 6: Documentation

## Design Decisions

### Format Specification

**Sh format** (`--format sh`):

```bash
export NAME="app"
export TAGS='["a","b"]'  # JSON array for complex types
export ENABLED="true"
export COUNT="42"
```

Used with `eval "$(bakefile export --format sh)"`

**Dotenv format** (`--format dotenv`):

```bash
NAME="app"
TAGS=["a","b"]
ENABLED=true
COUNT=42
```

Used for .env files and GitHub Actions ($GITHUB_ENV)

**JSON format** (`--format json`):

```json
{
    "name": "app",
    "tags": ["a", "b"],
    "enabled": true,
    "count": 42
}
```

**YAML format** (`--format yaml`):

```yaml
name: app
tags:
    - a
    - b
enabled: true
count: 42
```

### Type Conversion Strategy

| Pydantic Type | Shell/Dotenv     | JSON/YAML    |
| ------------- | ---------------- | ------------ |
| `str`         | `"value"`        | `"value"`    |
| `int`         | `"42"`           | `42`         |
| `float`       | `"3.14"`         | `3.14`       |
| `bool`        | `"true"`         | `true`       |
| `list[T]`     | `'["a","b"]'`    | `["a", "b"]` |
| `dict`        | `'{"k":"v"}'`    | `{"k": "v"}` |
| `None`        | `""` or `"null"` | `null`       |

**Key decision:** Complex types (list, dict, nested models) become JSON strings in shell/dotenv formats for `jq` compatibility.

### CLI Interface

```bash
bakefile export --format FORMAT [--output FILE]
```

Arguments:

- `--format`: Required choice from `sh`, `dotenv`, `json`, `yaml`
- `--output`: Optional file path (default: print to stdout)

## Key Files

### CLI Entry Point

**`src/bake/cli/bakefile/main.py`**

- Main bakefile CLI app
- Where new `export` command will be registered
- Uses `BakefileObject` for context

### Bakebook Loading

**`src/bake/bakebook/get.py`**

- `get_bakebook_from_target_dir_path()` - loads bakebook from bakefile.py
- `resolve_bakefile_path()` - finds bakefile.py in directory

### Bakebook Class

**`src/bake/bakebook/bakebook.py`**

- `Bakebook` extends `BaseSettings` from pydantic-settings
- Pydantic fields are the args to export
- Uses `model_config` for settings

### Bakefile Object

**`src/bake/cli/common/obj.py`**

- `BakefileObject` dataclass holds CLI context
- `get_bakebook()` method loads bakebook
- `bakefile_path` path to bakefile.py

### Example Bakebook

**`examples/simple/bakefile.py`**

```python
class MyBakebook(Bakebook):
    foo_url: str = "https://example.com"

    @command()
    def foo(self):
        console.echo(f"Doing foo with {self.foo_url}")
```

## Existing Patterns to Follow

### Command Structure (from `lint.py`)

```python
def lint(
    ctx: Context,
    only_bakefile: Annotated[bool, typer.Option(...)] = False,
) -> None:
    """Help text here"""
    bakefile_path = ctx.obj.bakefile_path
    # ... implementation
```

### Bakebook Loading Pattern

```python
from bake.cli.common.obj import get_bakefile_object

bakefile_obj = get_bakefile_object(rich_markup_mode=rich_markup_mode)
bakefile_obj.resolve_bakefile_path()
bakefile_obj.get_bakebook(allow_missing=False)
bakebook = bakefile_obj.bakebook
```

### Output to File Pattern

Use standard Python file I/O:

```python
if output_path:
    output_path.write_text(content)
else:
    console.echo(content)
```

## Quick Resume

To implement this feature:

1. **Create** `src/bake/cli/bakefile/export.py`
2. **Extract fields** from bakebook using Pydantic's `model_fields` attribute
3. **Convert** each field value based on target format
4. **Format** output (shell, dotenv, json, yaml)
5. **Register** command in `main.py`
6. **Test** with unit and integration tests

## Implementation Order

1. Start with Phase 1 (field extraction)
2. Then Phase 2 (formats - start with shell)
3. Then Phase 3 (CLI integration)
4. Test early, iterate
5. Add error handling and edge cases
6. Documentation last

## Dependencies

- **No new dependencies** for shell, dotenv, json (orjson already exists)
- **pyyaml** needed only for YAML format (consider deferring)
