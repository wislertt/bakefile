# Context: exclude_command_methods Feature

**Last Updated: 2026-03-02**

## Key Files

| File                                           | Purpose                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| `src/bake/bakebook/bakebook.py`                | Main implementation - add attribute + modify `_register_marked_methods()` |
| `src/bake/bakebook/decorator.py`               | `@command()` decorator (no changes needed)                                |
| `tests/unit/bake/bakebook/test_bakebook.py`    | Add unit tests                                                            |
| `tests/unit/bake/bakebook/test_inheritance.py` | Add inheritance-specific tests                                            |

## Key Code Locations

- `_register_marked_methods()` at line 54 - where filtering should happen
- `_get_command_kwargs()` at line 38 - MRO lookup logic (no changes needed)

## Dependencies

- `ClassVar` from `typing` (standard library)

## Edge Cases to Test

1. Empty list (default - no exclusions)
2. Exclude single method
3. Exclude multiple methods
4. Exclude method that doesn't exist (no error)
5. Exclude method that isn't a command (no error)
6. Multi-level inheritance (grandparent -> parent -> child)
