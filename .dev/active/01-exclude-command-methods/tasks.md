# Tasks: exclude_command_methods Feature

**Last Updated: 2026-03-02**

## Implementation

- [ ]   1. Add `exclude_command_methods: ClassVar[list[str]] = []` to `Bakebook` class
- [ ]   2. Modify `_register_marked_methods()` to filter out excluded methods
- [ ]   3. Add unit tests for basic exclusion
- [ ]   4. Add unit tests for edge cases (multi-level inheritance, non-existent methods)

## Verification

- [ ]   5. Run `bake test` to verify all tests pass
- [ ]   6. Run `bake lint` to verify code quality
