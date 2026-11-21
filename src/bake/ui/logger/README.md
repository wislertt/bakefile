# Logging

Coding rules live in `CODING_STANDARDS.md`.

## Logging

### Verbosity Levels

The bakefile CLI supports four verbosity levels via the `-v` flag:

| Flag   | Level    | Output                       |
| ------ | -------- | ---------------------------- |
| (none) | Silent   | No log output (verbosity=0)  |
| `-v`   | WARNING+ | Warnings and errors only     |
| `-vv`  | INFO+    | Info, warnings, and errors   |
| `-vvv` | DEBUG+   | All messages including debug |

Verbosity acts as a **global floor** — even if `bake_log` configures a module for DEBUG, the floor set by verbosity blocks messages below it.

### Logging in User Bakefiles

Users can use the standard Python `logging` module in their bakefiles:

```python
# In your bakefile.py
import logging
from bake import Bakebook

bakebook = Bakebook()


@bakebook.command()
def build():
    """Build the project."""
    logging.info("Starting build process...")
    logging.debug("Reading configuration...")
    # ... build logic ...
    logging.info("Build complete!")
```

The logging is automatically intercepted and formatted consistently with the CLI output.

### Unified Logging Configuration

Bakebook has three logging fields that work for both CLI and non-CLI usage:

```python
from bake import Bakebook


class MyBakebook(Bakebook):
    bake_log: str = "warning,bake=debug,myapp=debug"
    bake_log_verbosity: int = 0
    bake_log_pretty: bool = True
```

**BAKE_LOG format** (RUST_LOG-compatible, comma-separated):

```bash
# Simple global level
bake_log = "info"             # All modules at INFO
bake_log = "debug"            # All modules at DEBUG

# Global + per-module
bake_log = "warning,bake=debug"           # bake module at DEBUG, others at WARNING
bake_log = "info,myapp=debug,myapp.db=error"  # Multiple per-module overrides

# Per-module only (no global default)
bake_log = "myapp=debug"      # Only myapp logs, no global default
```

Valid level names: `critical`, `error`, `warning`, `warn`, `info`, `debug`

**Verbosity as floor:**

```python
# bake_log="debug" + verbosity=1 (WARNING floor)
bake -v build        # Only WARNING+ appears, DEBUG suppressed by floor

# bake_log="debug" + verbosity=3 (DEBUG floor)
bake -vvv build      # DEBUG appears, floor allows it
```

**Environment variable configuration:**

```bash
# .env
BAKE_LOG=warning,bake=debug,bakelib=debug
BAKE_LOG_VERBOSITY=1
BAKE_LOG_PRETTY=true
```

**Non-CLI usage:**

```python
from bake import Bakebook


class MyBakebook(Bakebook):
    bake_log: str = "info,myapp=debug"
    bake_log_verbosity: int = 2


bb = MyBakebook()
bb.setup_logging()  # Uses own bake_log and bake_log_verbosity
```

**Key points:**

- User bakefiles should use `logging` module (standard Python)
- Internal bakefile code uses `setup_logging()` with Loguru
- Standard `logging` calls are intercepted and routed to Loguru for consistent formatting
- Default output is JSON format (`is_pretty_log=False`) for machine parsing
- Use `is_pretty_log=True` for human-readable output in development

---
