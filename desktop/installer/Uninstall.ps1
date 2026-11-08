$ErrorActionPreference = "SilentlyContinue"
Get-Process DailySchedule | Stop-Process -Force
Remove-Item (Join-Path $env:LOCALAPPDATA "Programs\DailySchedule") -Recurse -Force
Remove-Item (Join-Path ([Environment]::GetFolderPath("Programs")) "Daily Schedule.lnk") -Force
Remove-Item (Join-Path ([Environment]::GetFolderPath("Desktop")) "Daily Schedule.lnk") -Force
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "DailySchedule"
Write-Host "Uninstalled. Your data in $env:APPDATA\DailySchedule was NOT deleted (remove it manually if you want a clean slate)."
