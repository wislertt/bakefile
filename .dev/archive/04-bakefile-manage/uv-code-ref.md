# UV Code References

**Status:** REFERENCE MATERIAL

These are links to the uv source code that were referenced during the implementation of the Python detection feature (see `.dev/archive/05-find-python/`).

---

## Code References

- "Found `{}` at `{}` ({source})",
  https://github.com/astral-sh/uv/blob/543f1f3f5924d1d2734fd718381e6f0d0f6f70b5/crates/uv-python/src/discovery.rs#L795

- source to str map (allow "virtual environment" and "active virtual environment")
  https://github.com/astral-sh/uv/blob/543f1f3f5924d1d2734fd718381e6f0d0f6f70b5/crates/uv-python/src/discovery.rs#L3169-L3184

- debug!("The {kind} environment's Python version satisfies the request: `{request}`");
  https://github.com/astral-sh/uv/blob/543f1f3f5924d1d2734fd718381e6f0d0f6f70b5/crates/uv/src/commands/project/mod.rs#L843
