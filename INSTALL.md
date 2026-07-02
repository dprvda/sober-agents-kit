# Installing the dprvda-kit

Two ways to adopt it, both driven by one cross-platform installer (`install.py`; the `.ps1`/`.sh`
files are thin wrappers). Requires **Python 3.9+** and **git**. `pre-commit` is installed/used if present.

## A. Into an existing repo (the common case)

```sh
git clone <this-repo> sober-agents-kit && cd sober-agents-kit
python install.py --target /path/to/your-repo [flags]
# Windows:  .\install.ps1 --target C:\path\to\your-repo [flags]
# bash:     ./install.sh   --target /path/to/your-repo [flags]
```

The installer:
1. Copies the payload into the target under `.claude/dprvda-kit/` (+ root config files).
   - An existing `CLAUDE.md` or `.pre-commit-config.yaml` is **never overwritten** — the kit's
     version is written alongside as `*.dprvda-kit.*` for you to merge.
   - An existing `.gitignore` is **appended to** (kit block), not replaced.
   - Any other clobbered file is backed up to `*.kit-bak`.
2. Installs requested packs and strips opted-out modules.
3. Substitutes `__PROJECT_NAME__` (default: target folder name).
4. **Sizes the SessionStart injector** to your repo's corpus (runs `inject_context_docs.py --count`
   and writes that many hook entries into `settings.json`).
5. Runs `pre-commit install` for the `pre-commit`, `commit-msg`, and `post-commit` stages.

## B. As a GitHub template (new repo)

Mark this repo as a template on GitHub (Settings → Template repository), then:
```sh
gh repo create my-new-repo --template <owner>/sober-agents-kit
cd my-new-repo
python install.py --here
```
`--here` promotes `template/` into the repo root in place.

## Flags

| Flag | Effect |
|---|---|
| `--target PATH` | target repo (existing-repo install) |
| `--here` | install into the current directory (template flow) |
| `--project-name NAME` | value for `__PROJECT_NAME__` (default: folder name) |
| `--project-owner OWN` | value for `__PROJECT_OWNER__` in `.mcp.json` |
| `--kit-name NAME` | namespace dir under `.claude/` (default: `dprvda-kit`) |
| `--rust` / `--python` | also install that language pack |
| `--no-ai-judge` | omit the AI code-review judge entirely |
| `--no-mcp` | omit `.mcp.json` + serena/github nudges |
| `--no-precommit` | skip `pre-commit install` |

## The AI-judge API key (shared `.env`)

The judge uses an OpenAI-compatible endpoint (defaults to DeepSeek). It reads `LLM_JUDGE_API_KEY`
from the environment, falling back to a gitignored **`.env`** at the repo root:

```
LLM_JUDGE_API_KEY=sk-...
# Recommended free judge — the NVIDIA build endpoint (key at https://build.nvidia.com):
# LLM_JUDGE_BASE_URL=https://integrate.api.nvidia.com
# LLM_JUDGE_MODEL=mistralai/mistral-medium-3.5-128b
# (any OpenAI-compatible host works — the gates call {BASE_URL}/v1/chat/completions)
```

A low-balance key can be handed to a trusted collaborator directly in `.env` — no 1Password needed.
**If the key is blank, the judge soft-passes** (commits still go through), so the kit is fully usable
without it. Edit the prompts in `.claude/dprvda-kit/gates/prompts/*.md` any time.

> Prefer 1Password? `template/.op-claude.env.example` shows the `op run --env-file=.op-claude.env -- claude`
> pattern instead.

## Verify it works

```sh
cd /path/to/your-repo
# 1. dangerous-git hook (should print a block, exit non-zero):
echo '{"tool_input":{"command":"git push --force"}}' | python .claude/dprvda-kit/hooks/block-dangerous-git.py; echo "rc=$?"
# 2. gates dispatcher on a commit:
git add -A && git commit -m "chore(meta): adopt dprvda-kit"
# 3. SessionStart injector count matches settings.json:
python .claude/dprvda-kit/inject_context_docs.py --count
```

A script without a `# REASON:` header will be blocked by `check_file_reason`; a hardcoded key will be
blocked by `check_secrets`; a broken `.md` link by `check_links`.

## Enabling a pack later

Re-run the installer with `--rust`/`--python`, or follow the manual steps in `packs/<lang>/README.md`.

## Uninstall

```sh
python uninstall.py --target /path/to/your-repo
```
Conservative by design: it removes `.claude/dprvda-kit/`, restores `*.kit-bak` backups, removes
root files only if still unmodified, and lists anything customized for you to remove manually.

## Troubleshooting

- **`pre-commit: command not found`** → `pip install pre-commit`, then re-run with `--no-precommit`
  already done, or just `pre-commit install` yourself.
- **Judge never runs** → expected if `LLM_JUDGE_API_KEY` is blank (soft-pass). Set it in `.env`.
- **A gate is too strict for your repo** → its thresholds/exempt-dirs are constants at the top of the
  gate script; edit them. Gates are meant to be tuned per repo.
- **Windows consoles** → all hooks emit ASCII and never hard-fail the session on encoding issues.
