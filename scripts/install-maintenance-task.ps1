param([string]$TaskName = 'FMSC Portal Daily Maintenance', [string]$At = '09:00')
$ErrorActionPreference = 'Stop'
$portalRoot = Split-Path $PSScriptRoot -Parent
$runnerPath = Join-Path $PSScriptRoot 'run-maintenance.ps1'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) { throw 'A task with this name exists. Review it in Task Scheduler before changing it.' }
$triggerTime = [DateTime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $runnerPath + '"'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $portalRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$options = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $options -Description 'Back up FMSC data and send pending reminders; runs while this user is signed in.'
