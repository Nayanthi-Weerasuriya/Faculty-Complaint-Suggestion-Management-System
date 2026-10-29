param([string]$FilePath = (Join-Path (Split-Path $PSScriptRoot -Parent) '.env'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { throw 'Create .env from .env.example and fill in your values first.' }
foreach ($line in Get-Content -LiteralPath $FilePath) {
    $entry = $line.Trim()
    if (-not $entry -or $entry.StartsWith('#')) { continue }
    if ($entry -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { throw 'Invalid .env entry. Use NAME=value, one per line.' }
    $settingName = $Matches[1]
    $settingValue = $Matches[2].Trim()
    if ($settingValue.Length -ge 2 -and (($settingValue.StartsWith('"') -and $settingValue.EndsWith('"')) -or ($settingValue.StartsWith("'") -and $settingValue.EndsWith("'")))) {
        $settingValue = $settingValue.Substring(1, $settingValue.Length - 2)
    }
    [Environment]::SetEnvironmentVariable($settingName, $settingValue, 'Process')
}
