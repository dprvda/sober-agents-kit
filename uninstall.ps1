# Thin wrapper around uninstall.py.
# Usage:  .\uninstall.ps1 --target C:\path\to\repo
python "$PSScriptRoot\uninstall.py" @args
exit $LASTEXITCODE
