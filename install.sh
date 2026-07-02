#!/usr/bin/env bash
# Thin wrapper around install.py (the real cross-platform installer).
# Usage:  ./install.sh --target /path/to/repo [--rust] [--python] [--no-ai-judge] ...
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$DIR/install.py" "$@"
