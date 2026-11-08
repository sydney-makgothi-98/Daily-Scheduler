<#
 Installs Daily Schedule for the current user (no admin rights needed).
 Run:  right-click Install.ps1 -> Run with PowerShell   (or: powershell -ExecutionPolicy Bypass -File Install.ps1)
#>
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "DailySchedule"
if (-not (Test-Path (Join-Path $src "DailySchedule.exe"))) { throw "DailySchedule folder not found next to this script." }

$dest = Join-Path $env:LOCALAPPDATA "Programs\DailySchedule"
Get-Process DailySchedule -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Copy-Item $src $dest -Recurse
$exe = Join-Path $dest "DailySchedule.exe"

$shell = New-Object -ComObject WScript.Shell
foreach ($dir in @([Environment]::GetFolderPath("Programs"), [Environment]::GetFolderPath("Desktop"))) {
    $lnk = $shell.CreateShortcut((Join-Path $dir "Daily Schedule.lnk"))
    $lnk.TargetPath = $exe
    $lnk.WorkingDirectory = $dest
    $lnk.Save()
}

# Start with Windows (alarms only ring while the app is running). Toggle later from the tray icon.
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "DailySchedule" -Value "`"$exe`" --background"

Start-Process $exe
Write-Host "Installed to $dest. Your data lives in $env:APPDATA\DailySchedule and is kept on updates/uninstall."
