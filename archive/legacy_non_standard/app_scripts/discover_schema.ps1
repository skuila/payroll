Param(
  [string]$Dsn = $null
)

$ErrorActionPreference = "Stop"

function Get-PsqlPath {
  $cmd = $null
  try { $cmd = (Get-Command psql -ErrorAction SilentlyContinue).Source } catch {}
  if ($cmd) { return $cmd }
  $candidate = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($candidate) { return $candidate.FullName }
  throw "psql introuvable (PATH et C:\Program Files\PostgreSQL\*\bin)"
}

if (-not $Dsn) {
  # Préférer une variable d'environnement pour éviter d'avoir un mot de passe en clair
  if ($env:DATABASE_DSN) { $Dsn = $env:DATABASE_DSN }
  elseif ($env:PAYROLL_DSN) { $Dsn = $env:PAYROLL_DSN }
  else {
    Write-Warning "Aucun DSN fourni: définissez -Dsn ou la variable d'environnement DATABASE_DSN. Utilisation d'un placeholder non sécurisé."
    $Dsn = 'postgresql://postgres:<REDACTED>@localhost:5432/payroll_db'
  }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$outDir = Join-Path $root "logs\\analytics"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$psql = Get-PsqlPath

$sql = @"
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE (table_schema='paie' AND table_name='stg_paie_transactions')
   OR (table_schema='payroll' AND table_name='payroll_transactions')
   OR (table_schema='core' AND table_name='employees')
ORDER BY table_schema, table_name, ordinal_position;
"@

$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $sql -Encoding UTF8
& $psql $Dsn "-t" "-A" "-F" ";" "-f" $tmp | Out-File -FilePath (Join-Path $outDir "schema_columns.csv") -Encoding UTF8
Remove-Item $tmp -Force

Write-Host "Colonnes exportees vers $(Join-Path $outDir 'schema_columns.csv')"

# Afficher un résumé à l'écran
Write-Host ""
Write-Host "Tables disponibles (paie/payroll/core):"
$sql2 = @"
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema in ('paie','payroll','core')
ORDER BY table_schema, table_name;
"@
$tmp2 = New-TemporaryFile
Set-Content -Path $tmp2 -Value $sql2 -Encoding UTF8
& $psql $Dsn "-t" "-A" "-F" ";" "-f" $tmp2
Remove-Item $tmp2 -Force

Write-Host ""
Write-Host "Colonnes stg_paie_transactions (si table existe):"
$sql3 = @"
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema='paie' AND table_name='stg_paie_transactions'
ORDER BY ordinal_position;
"@
$tmp3 = New-TemporaryFile
Set-Content -Path $tmp3 -Value $sql3 -Encoding UTF8
& $psql $Dsn "-t" "-A" "-F" ";" "-f" $tmp3
Remove-Item $tmp3 -Force


