# Plan: exclude_command_methods Feature

**Last Updated: 2026-03-02**

## Summary

Add a class-level configuration to exclude inherited `@command()` methods from being registered in child Bakebook classes.

## Problem

- Commands are inherited via MRO (always active in child classes)
- No way to opt-out of inherited commands
- User wants to remove specific commands from parent classes

## Solution

Add `exclude_command_methods: ClassVar[list[str]]` attribute to exclude methods by name.

```python
class ParentBakebook(Bakebook):
    @command()
    def deploy(self): ...

class ChildBakebook(ParentBakebook):
    exclude_command_methods: ClassVar[list[str]] = ["deploy"]
```

## Design Decisions

| Decision       | Choice                         | Rationale                               |
| -------------- | ------------------------------ | --------------------------------------- |
| Key type       | Method name (not command name) | Pythonic, references actual method      |
| Attribute type | `ClassVar[list[str]]`          | Class-level config, not Pydantic field  |
| Visibility     | Public (no underscore)         | Intentional configuration, not internal |

## Implementation

1. Add `exclude_command_methods: ClassVar[list[str]] = []` to `Bakebook`
2. Modify `_register_marked_methods()` to filter excluded methods
3. Add unit tests
