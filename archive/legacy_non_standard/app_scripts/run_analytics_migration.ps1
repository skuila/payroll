Param(
  [string]$Host = $env:PGHOST,
  [string]$Port = $env:PGPORT,
  [string]$Db   = $env:PGDATABASE,
  [string]$User = $env:PGUSER
)

if (-not $Host -or -not $Port -or -not $Db -or -not $User) {
  Write-Error "Veuillez définir PGHOST, PGPORT, PGDATABASE, PGUSER (et PGPASSWORD) dans l'environnement, ou passer les paramètres -Host -Port -Db -User."
  exit 1
}

$ErrorActionPreference = "Stop"

function Run-SqlFile {
  param([string]$FilePath)
  if (-not (Test-Path $FilePath)) {
    Write-Error "Fichier SQL introuvable: $FilePath"
  }
  Write-Host "==> Exécution: $FilePath"
  & psql "-h" $Host "-p" $Port "-U" $User "-d" $Db "-v" "ON_ERROR_STOP=1" "-f" $FilePath
}

try {
  $root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
  $migrationDir = Join-Path $root "migration"

  Run-SqlFile (Join-Path $migrationDir "apply_analytics.sql")
  Run-SqlFile (Join-Path $migrationDir "analytics_validation.sql")

  Write-Host "Migration Analytics terminee avec succes." -ForegroundColor Green
} catch {
  Write-Error ("Echec migration: {0}" -f $($_.Exception.Message))
  exit 2
}


