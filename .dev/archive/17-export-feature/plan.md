# Export Feature - Implementation Plan

Last Updated: 2026-01-17

## Executive Summary

Implement `bakefile export` command to export Pydantic-validated args from bakebook to external formats (shell, dotenv, JSON, YAML). This bridges Python runtime configs with shell ecosystem tools, enabling use in GitHub Actions, Docker, and other non-Python contexts.

**Primary Use Case:** GitHub Actions - export bakebook args as shell environment variables.

## Current State

- **Bakebook** extends `BaseSettings` from pydantic-settings
- Args are defined as Pydantic fields (e.g., `foo_url: str = "https://example.com"`)
- Bakebook supports validation via Pydantic
- Existing `bakefile` CLI commands: `init`, `add_inline`, `find_python`, `lint`, `uv` (sync, lock, add, pip)
- CLI structure in `src/bake/cli/bakefile/`

## Proposed Future State

New `bakefile export` command:

```bash
bakefile export --format sh       # stdout: export KEY="value"
bakefile export --format sh --output config.sh  # write to file
bakefile export --format dotenv   # stdout: KEY="value"
bakefile export --format json     # stdout: {"key": "value"}
bakefile export --format yaml     # stdout: key: value
bakefile export --format json --output config.json
```

**GitHub Actions usage:**

```yaml
- name: Load bakebook config
  run: eval "$(bakefile export --format sh)"

- name: Export to GH Actions env
  run: bakefile export --format dotenv >> $GITHUB_ENV
```

## Implementation Phases

### Phase 1: Core Export Logic (2-3 hours)

Implement the core export functionality that extracts Pydantic model fields and converts them to different formats.

**Tasks:**

1. **Create export module structure**
    - File: `src/bake/cli/bakefile/export.py`
    - Acceptance: Module created with basic function stubs
    - Effort: S

2. **Implement field extraction from Bakebook**
    - Extract all Pydantic fields (excluding private attrs, Pydantic internals)
    - Handle nested models, complex types
    - Acceptance: Can iterate over bakebook fields and get name/value pairs
    - Effort: M

3. **Implement type conversion strategy**
    - Primitives (str, int, float, bool) → direct values
    - Complex types (list, dict, nested models) → JSON strings
    - Acceptance: All Pydantic types convert correctly
    - Effort: M

### Phase 2: Format Implementations (2-3 hours)

Implement each output format with proper serialization.

**Tasks:**

4. **Sh format**
    - Output: `export KEY="value"` syntax
    - Complex types as JSON strings: `export TAGS='["a","b"]'`
    - Acceptance: Output valid for `eval`
    - Effort: M

5. **Dotenv format**
    - Output: `KEY="value"` syntax (no `export` keyword)
    - Compatible with .env files, $GITHUB_ENV
    - Acceptance: Valid dotenv format
    - Effort: S

6. **JSON format**
    - Use Pydantic's `model_dump()`
    - Pretty-print with orjson (existing dependency)
    - Acceptance: Valid JSON output
    - Effort: S

7. **YAML format**
    - Convert to YAML using pyyaml
    - Acceptance: Valid YAML output
    - Effort: S

### Phase 3: CLI Integration (1-2 hours)

Integrate export command into bakefile CLI.

**Tasks:**

8. **Add export command to bakefile app**
    - File: `src/bake/cli/bakefile/main.py`
    - Register command with Typer
    - Acceptance: `bakefile export` shows in help
    - Effort: S

9. **Implement CLI parameters**
    - `--format` choice option (sh, dotenv, json, yaml)
    - `--output` file option (optional, writes to file; default: stdout)
    - Acceptance: CLI accepts all parameters
    - Effort: M

10. **Wire up bakebook loading**
    - Use existing `get_bakebook_from_target_dir_path()`
    - Handle missing bakebook gracefully
    - Acceptance: Loads bakebook correctly
    - Effort: M

### Phase 4: Error Handling & Edge Cases (1-2 hours)

**Tasks:**

11. **Handle missing bakebook**
    - Clear error message
    - Exit code 1
    - Acceptance: Graceful failure
    - Effort: S

12. **Handle empty bakebook (no args)**
    - Output empty format appropriately
    - Acceptance: No crash on empty
    - Effort: S

13. **Handle special characters in values**
    - Quote escaping for shell/dotenv
    - JSON encoding for complex values
    - Acceptance: Special chars handled correctly
    - Effort: M

14. **Validate --output file path**
    - Check directory exists
    - Create file if not exists
    - Acceptance: File writing works
    - Effort: S

### Phase 5: Testing (2-3 hours)

**Tasks:**

15. **Unit tests for format converters**
    - File: `tests/unit/bake/cli/bakefile/test_export.py`
    - Test each format with various types
    - Acceptance: All formats tested
    - Effort: M

16. **Unit tests for CLI**
    - Test parameter parsing
    - Test bakebook loading
    - Test error cases
    - Acceptance: CLI behavior tested
    - Effort: M

17. **Integration tests**
    - File: `tests/integration/fixtures/test_export.py`
    - Test against actual bakefile with real args
    - Test output to file
    - Acceptance: End-to-end tested
    - Effort: M

### Phase 6: Documentation (1 hour)

**Tasks:**

18. **Add CLI help text**
    - Command description
    - Parameter descriptions
    - Examples in help
    - Acceptance: `bakefile export --help` is useful
    - Effort: S

19. **Update project README (if needed)**
    - Document export command
    - Add GitHub Actions example
    - Acceptance: Feature documented
    - Effort: S

## Risk Assessment and Mitigation

| Risk                                         | Impact | Probability | Mitigation                                           |
| -------------------------------------------- | ------ | ----------- | ---------------------------------------------------- |
| Complex Pydantic types don't convert cleanly | High   | Medium      | Use JSON strings for complex types, document clearly |
| Shell quoting issues break eval              | High   | Low         | Use shlex.quote or careful escaping, test thoroughly |
| YAML adds new dependency                     | Low    | Low         | Use existing or minimal import                       |
| Naming conflicts (invalid shell var names)   | Medium | Medium      | Sanitize names or document constraints               |

## Success Metrics

- All unit tests pass
- Integration test passes with real bakefile
- GitHub Actions example works
- `make lint` passes
- `make test` passes
- No new dependencies added (except possibly pyyaml)

## Required Resources and Dependencies

**Existing dependencies:**

- typer (CLI)
- pydantic-settings (Bakebook base)
- orjson (JSON, already used)
- pytest (testing)

**Potential new dependencies:**

- pyyaml (for YAML format) - OR skip YAML in v1

**Files to create/modify:**

- `src/bake/cli/bakefile/export.py` (new)
- `src/bake/cli/bakefile/main.py` (modify)
- `tests/unit/bake/cli/bakefile/test_export.py` (new)
- `tests/integration/fixtures/test_export.py` (new)

## Timeline Estimates

- Phase 1: 2-3 hours
- Phase 2: 2-3 hours
- Phase 3: 1-2 hours
- Phase 4: 1-2 hours
- Phase 5: 2-3 hours
- Phase 6: 1 hour

**Total: 9-14 hours**

## Open Questions

1. **Skip YAML in v1?** Could reduce initial scope and avoid new dependency.
2. **Include/exclude filtering?** Probably not needed for v1 - export all by default.
3. **Secrets handling?** Out of scope for v1 - users should manage secrets via existing mechanisms.
