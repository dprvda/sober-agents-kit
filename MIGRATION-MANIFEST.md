# MIGRATION-MANIFEST - sober-agents-kit

Born on Windows 11; frozen 2026-08. The machine migrated to Ubuntu Linux; nothing here was
ported. Read `docs/planning/linux-migration-2026-08-20.md` + `linux-system-setup-2026-08-20.md`
in dprvda/pravda-automations-page (or `E:\LINUX-BOOTSTRAP\` on the old data SSD) before reviving.

## Clones
TWO working copies existed on the old machine, both -> github.com/dprvda/sober-agents-kit:
`Documents\sober-agents-kit` and `Documents\claude-code-kit` (the older dir name). Clone fresh
on Linux; do not restore either working tree from the mirror.

## Data (gitignored / external)
None load-bearing. Any stray local files live in the mirror at
`E:\migration-mirror\C\Users\dprvd\Documents\sober-agents-kit\` and `...\claude-code-kit\`
(the latter's 12 probe scripts were frozen to branch `wip/migration-freeze`).

## Services + scheduled tasks
None. This repo ran nothing on the Windows scheduler.

## Windows coupling
None known beyond possible `C:/Users/dprvd` paths in docs/examples - grep before use on Linux.

## Secrets
No env files were harvested from this repo (none existed at freeze time).
