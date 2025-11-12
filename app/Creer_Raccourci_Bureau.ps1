# Script PowerShell pour créer un raccourci sur le bureau
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "PayrollAnalyzer.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$PSScriptRoot\LANCER_APP.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Description = "Payroll Analyzer - Application de Paie"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,165"
$Shortcut.Save()

Write-Host "✅ Raccourci créé sur le bureau: PayrollAnalyzer.lnk"
Write-Host ""
Write-Host "Double-cliquez sur le raccourci pour lancer l'application."

