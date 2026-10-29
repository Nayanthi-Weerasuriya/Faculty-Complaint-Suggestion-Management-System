param([string]$PythonPath = '', [ValidateRange(1,3650)][int]$ReminderDays = 7)
$ErrorActionPreference = 'Stop'
$portalRoot = Split-Path $PSScriptRoot -Parent
if (-not $PythonPath) { $PythonPath = Join-Path $portalRoot 'venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw 'Set PythonPath to the project virtual environment Python.' }
if (Test-Path -LiteralPath (Join-Path $portalRoot '.env')) { . (Join-Path $PSScriptRoot 'load-environment.ps1') }
Push-Location -LiteralPath $portalRoot
try {
    # Preserve the database and media first, even if reminder delivery later fails.
    & $PythonPath manage.py backup_portal
    if ($LASTEXITCODE -ne 0) { throw 'Backup failed; maintenance stopped.' }
    & $PythonPath manage.py send_pending_reminders --days $ReminderDays
    if ($LASTEXITCODE -ne 0) { throw 'Pending reminders failed.' }
} finally {
    Pop-Location
}
