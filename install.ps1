# Thin wrapper around install.py (the real cross-platform installer).
# Usage:  .\install.ps1 --target C:\path\to\repo [--rust] [--python] [--no-ai-judge] ...
python "$PSScriptRoot\install.py" @args
exit $LASTEXITCODE
