#!/usr/bin/env bash
# Thin wrapper around uninstall.py.
# Usage:  ./uninstall.sh --target /path/to/repo
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$DIR/uninstall.py" "$@"
