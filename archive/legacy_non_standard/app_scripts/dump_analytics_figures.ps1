Param(
  [string]$PgHost = $env:PGHOST,
  [string]$PgPort = $env:PGPORT,
  [string]$PgDb   = $env:PGDATABASE,
  [string]$PgUser = $env:PGUSER,
  [string]$Dsn  = $null
)

$ErrorActionPreference = "Stop"

# Résolution dynamique de psql
function Get-PsqlPath {
  $cmd = $null
  try { $cmd = (Get-Command psql -ErrorAction SilentlyContinue).Source } catch {}
  if ($cmd) { return $cmd }
  $candidate = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($candidate) { return $candidate.FullName }
  throw "psql introuvable (PATH et C:\Program Files\PostgreSQL\*\bin)"
}

# Construire DSN si non fourni
if (-not $Dsn) {
  if ($PgHost -and $PgPort -and $PgDb -and $PgUser -and $env:PGPASSWORD) {
    $Dsn = \"postgresql://${PgUser}:${env:PGPASSWORD}@${PgHost}:${PgPort}/${PgDb}\"
  } else {
    # Valeurs par défaut du projet (voir api/config.py)
    # Préférer utiliser DATABASE_DSN ou PAYROLL_DSN pour éviter des mots de passe codés en dur
    if ($env:DATABASE_DSN) { $Dsn = $env:DATABASE_DSN }
    elseif ($env:PAYROLL_DSN) { $Dsn = $env:PAYROLL_DSN }
    else { Write-Warning "Aucun DSN sécurisé fourni; utilisez DATABASE_DSN. Utilisation d'un placeholder."; $Dsn = 'postgresql://postgres:<REDACTED>@localhost:5432/payroll_db' }
  }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$outDir = Join-Path $root "logs\\analytics"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$psqlPath = Get-PsqlPath
$migrationDir = Join-Path $root "migration"

# Assurer la création/MAJ des vues (idempotent)
& $psqlPath $Dsn "-v" "ON_ERROR_STOP=1" "-f" (Join-Path $migrationDir "apply_analytics.sql") | Out-Null

function Run-QueryToFile {
  param([string]$Sql, [string]$OutFile)
  $tmp = New-TemporaryFile
  Set-Content -Path $tmp -Value $Sql -Encoding UTF8
  & $psqlPath $Dsn "-v" "ON_ERROR_STOP=1" "-t" "-A" "-F" ";" "-f" $tmp | Out-File -FilePath $OutFile -Encoding UTF8
  Remove-Item $tmp -Force
}

# 1) Derniere date
Run-QueryToFile @"
SELECT coalesce(to_char(MAX(date_paie),'YYYY-MM-DD'),'') AS last_pay_date
FROM paie.v_lignes_paie;
"@ (Join-Path $outDir "last_date.txt")

# 2) Masse pour la derniere date (masse = gains + part_employeur)
Run-QueryToFile @"
WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
SELECT to_char(m.date_paie,'YYYY-MM-DD') AS date_paie,
       m.masse_salariale, m.gains, m.deductions, m.part_employeur
FROM paie.v_masse_salariale m
JOIN d ON d.dp = m.date_paie;
"@ (Join-Path $outDir "masse_last.csv")

# 3) Top 10 codes
Run-QueryToFile @"
WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
SELECT c.code_paie, c.categorie_paie,
       c.total_combine, c.part_employeur, c.lignes
FROM paie.v_categories c
JOIN d ON d.dp = c.date_paie
ORDER BY ABS(c.total_combine) DESC
LIMIT 10;
"@ (Join-Path $outDir "codes_top10.csv")

# 4) Top 10 postes
Run-QueryToFile @"
WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
SELECT p.poste_budgetaire, p.description_poste_budgetaire,
       p.total_combine, p.part_employeur, p.gains, p.deductions
FROM paie.v_postes p
JOIN d ON d.dp = p.date_paie
ORDER BY ABS(p.total_combine) DESC
LIMIT 10;
"@ (Join-Path $outDir "postes_top10.csv")

# 5) Top 10 employes
Run-QueryToFile @"
WITH d AS (SELECT MAX(date_paie) AS dp FROM paie.v_lignes_paie)
SELECT e.matricule, e.nom_employe,
       e.total_combine, e.gains, e.deductions, e.part_employeur, e.lignes
FROM paie.v_employes e
JOIN d ON d.dp = e.date_paie
ORDER BY ABS(e.total_combine) DESC
LIMIT 10;
"@ (Join-Path $outDir "employes_top10.csv")

Write-Host "Chiffres exportes dans $outDir"
Write-Host ""
Write-Host "Derniere date:"
Get-Content (Join-Path $outDir "last_date.txt")
Write-Host ""
Write-Host "Masse (derniere date):"
Get-Content (Join-Path $outDir "masse_last.csv")
Write-Host ""
Write-Host "Top 10 codes:"
Get-Content (Join-Path $outDir "codes_top10.csv")
Write-Host ""
Write-Host "Top 10 postes:"
Get-Content (Join-Path $outDir "postes_top10.csv")
Write-Host ""
Write-Host "Top 10 employes:"
Get-Content (Join-Path $outDir "employes_top10.csv")


