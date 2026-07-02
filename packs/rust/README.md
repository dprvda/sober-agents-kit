# Rust pack

Optional Rust supply-chain + binary-hardening gates for the dprvda-kit. The fastest way to enable
them is `install.ps1 --rust` (or `install.sh --rust`), which copies these into
`.claude/dprvda-kit/gates/` and registers them. Manual steps are below.

| File | What it checks | Blocks on | Needs |
|---|---|---|---|
| `check_cargo_audit.py` | RustSec advisories in `Cargo.lock` | any unfixed advisory | `cargo install cargo-audit` |
| `check_cargo_vet.py` | supply-chain trust via `cargo vet` | a new dep without audit/exemption | `cargo install cargo-vet --locked` |
| `check_binary_secrets.py` | secret-shaped strings in compiled binaries | any secret pattern in the artifact | — |

All follow the kit's **unavailable_pass** policy: if the required tool isn't installed, the gate
exits 0 with a stderr warning instead of breaking a fresh checkout.

## Manual enable

1. Copy the gates into the kit's gates dir:
   ```sh
   cp packs/rust/gates/*.py <target>/.claude/dprvda-kit/gates/
   ```
2. Register the two cargo gates in `.claude/dprvda-kit/gates/run_gates_parallel.py` — append to `PHASE2_GATES`:
   ```python
   ("check_cargo_audit", "check_cargo_audit.py", True),
   ("check_cargo_vet",   "check_cargo_vet.py",   True),
   ```
   (The dispatcher skips any gate whose file is absent, so order doesn't matter.)
3. `check_binary_secrets.py` is best wired as a standalone `.pre-commit-config.yaml` hook so it scans
   built artifacts rather than running on every doc commit:
   ```yaml
   - id: dprvda-kit-binary-secrets
     name: scan compiled binaries for secret-shaped strings
     entry: python .claude/dprvda-kit/gates/check_binary_secrets.py
     language: system
     always_run: true
     pass_filenames: false
   ```
   Then edit the `BINARIES` list in that script to your actual compiled-output paths.

## Install hints

```sh
cargo install cargo-audit
cargo install cargo-vet --locked
cargo vet init        # once, to create the supply-chain/ baseline
```

`check_binary_secrets.py` uses `strings` when present and falls back to a pure-Python scan otherwise.
