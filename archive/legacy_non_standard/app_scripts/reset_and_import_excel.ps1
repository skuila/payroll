Param(
  # Pour éviter de mettre des mots de passe en clair dans le dépôt, passez les DSN en param
  # ou définissez la variable d'environnement DATABASE_DSN / PAYROLL_DSN avant d'exécuter ce script.
  [string]$DsnAdmin = '',
  [string]$DsnApp   = '',
  [string]$ExcelPath,
  [string]$Sheet = $null
)

$ErrorActionPreference = "Stop"

function Get-PsqlPath {
  $cmd = $null
  try { $cmd = (Get-Command psql -ErrorAction SilentlyContinue).Source } catch {}
  if ($cmd) { return $cmd }
  $candidate = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($candidate) { return $candidate.FullName }
  throw "psql introuvable"
}

if (-not (Test-Path $ExcelPath)) { throw "Fichier Excel introuvable: $ExcelPath" }

$psql = Get-PsqlPath

if (-not $DsnAdmin) {
  if ($env:DATABASE_DSN) { $DsnAdmin = $env:DATABASE_DSN }
  elseif ($env:PAYROLL_DSN) { $DsnAdmin = $env:PAYROLL_DSN }
  else { Write-Warning "Aucun DsnAdmin fourni: définissez -DsnAdmin ou la variable d'environnement DATABASE_DSN. Utilisation d'un placeholder non sécurisé."; $DsnAdmin = 'postgresql://postgres:<REDACTED>@localhost:5432/payroll_db' }
}

Write-Host "== VIDAGE des données staging/fact =="
& $psql $DsnAdmin -v ON_ERROR_STOP=1 -c "TRUNCATE TABLE paie.stg_paie_transactions RESTART IDENTITY;" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Echec TRUNCATE staging" }

Write-Host "== IMPORT depuis Excel =="
if ($Sheet) {
  py .\scripts\import_excel_to_staging.py --dsn $DsnAdmin --file $ExcelPath --sheet $Sheet --truncate
} else {
  py .\scripts\import_excel_to_staging.py --dsn $DsnAdmin --file $ExcelPath --truncate
}

if ($LASTEXITCODE -ne 0) { throw "Echec import Excel" }

Write-Host "== Rafraichir vues (idempotent) =="
& $psql $DsnAdmin -v ON_ERROR_STOP=1 -f .\migration\apply_analytics.sql | Out-Null

Write-Host "Termine. Donnees reinitialisees et fichier importe." -ForegroundColor Green





