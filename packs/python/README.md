# Python pack

Optional Python lint gate for the agent-kit. Enable with `install.ps1 --python`
(or `install.sh --python`), which copies it into `.agent-kit/gates/` and registers it.

| File | What it checks | Blocks on | Needs |
|---|---|---|---|
| `check_python_lint.py` | staged `.py` files via `ruff check` | any ruff error | `pip install ruff` |

Follows the kit's **unavailable_pass** policy: if `ruff` isn't installed, it exits 0 with a notice.

> `.py` files are already covered by the core `check_file_reason` gate (the `# REASON:` header).
> This pack adds a separate ruff pass for lint correctness — undefined names, unused imports/vars,
> and style issues that `check_file_reason` doesn't inspect.

## Manual enable

1. Copy the gate:
   ```sh
   cp packs/python/gates/check_python_lint.py <target>/.agent-kit/gates/
   ```
2. Register it in `.agent-kit/gates/run_gates_parallel.py` — append to `PHASE2_GATES`:
   ```python
   ("check_python_lint", "check_python_lint.py", True),
   ```

## Install hint

```sh
pip install ruff
```

A `pyproject.toml` or `ruff.toml` at the repo root controls the enabled rules. Without one, ruff
defaults to the `E`/`F` sets (pycodestyle + pyflakes) — the highest-impact errors with little noise.
