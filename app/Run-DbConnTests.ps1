<#
Run-DbConnTests.ps1
Objectif : vérifier la stratégie stricte de connexion PostgreSQL en 3 cas :
A) DSN absent  B) DSN invalide  C) DSN valide
Le script :
- Sauvegarde/restaure .env
- Modifie temporairement le DSN
- Lance l'app et collecte exit code + logs
Prérequis : votre lanceur (ex: launch_payroll.py) termine son process quand on ferme l'app.
#>

param(
  [string]$Entry = "launch_payroll.py",                # ou "payroll_app_qt_Version4.py"
  [string]$PythonPath = "..\.venv\Scripts\python.exe", # chemin vers python du venv
  [int]$TimeoutSec = 60,                               # délai max par cas (à vous de fermer l'app si UI)
  [string]$ValidDsn = ""                               # si vide, on le lit depuis .env
)

function Resolve-Python {
  param([string]$Path)
  if (Test-Path $Path) { return (Resolve-Path $Path).Path }
  if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
  Write-Error "Python introuvable : $Path"
  exit 1
}

function Read-EnvFile {
  # Prefer app/.env (the application reads that). Fall back to repo root .env if missing.
  $envPath = "./app/.env"
  if (!(Test-Path $envPath)) {
    $envPath = "./.env"
    if (!(Test-Path $envPath)) { return @{} }
  }
  $h = @{}
  Get-Content $envPath | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $kv = $_ -split "=", 2
    if ($kv.Count -eq 2) { $h[$kv[0].Trim()] = $kv[1].Trim() }
  }
  return $h
}

function Write-EnvFile {
  param([hashtable]$Vars)
  $lines = @()
  foreach ($k in $Vars.Keys) { $lines += "$k=$($Vars[$k])" }
  # Write to app/.env so the application picks it up consistently
  $envPath = "./app/.env"
  Set-Content $envPath -Value $lines -Encoding UTF8
}

function Mask-DSN {
  param([string]$dsn)
  if ([string]::IsNullOrWhiteSpace($dsn)) { return $dsn }
  return ($dsn -replace "(?<=://[^:@/]+:)([^@]*)(?=@)", "***")
}

function Make-InvalidDsn {
  param([string]$dsn)
  if ($dsn -match "(?<=://[^:@/]+:)([^@]*)(?=@)") {
    return ($dsn -replace "(?<=://[^:@/]+:)([^@]*)(?=@)", "WRONGPWD")
  } elseif ($dsn -match "^postgresql://[^:@/]+@") {
    # pas de mot de passe -> en injecter un faux
    return ($dsn -replace "^postgresql://([^:@/]+)@", "postgresql://`$1:WRONGPWD@")
  } else {
    return $dsn + "#bad" # dernier recours
  }
}

function Make-ValidDsn {
  param([string]$dsn, [string]$password)
  if ([string]::IsNullOrWhiteSpace($dsn) -or [string]::IsNullOrWhiteSpace($password)) { return $dsn }
  # Insert password into URL-style DSN
  try {
    $parts = $dsn -split '@', 2
    if ($parts.Count -eq 2) {
      $userHost = $parts[0] + ':' + $password + '@' + $parts[1]
      return $userHost
    }
  } catch {}
  return $dsn
}

function Run-App {
  param([string]$Python, [string]$Entry, [string]$LogBase, [int]$TimeoutSec, [hashtable]$EnvVars = @{})

  $so = "$LogBase.out.txt"
  $se = "$LogBase.err.txt"
  if (Test-Path $so) { Remove-Item $so -Force }
  if (Test-Path $se) { Remove-Item $se -Force }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $Python
  $psi.Arguments = $Entry
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.WorkingDirectory = (Get-Location).Path

  # Set environment variables for the subprocess
  foreach ($key in $EnvVars.Keys) {
    $psi.EnvironmentVariables[$key] = $EnvVars[$key]
  }

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  $sw = [Diagnostics.Stopwatch]::StartNew()
  while (-not $p.HasExited -and $sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    Start-Sleep -Milliseconds 200
  }
  if (-not $p.HasExited) {
    Write-Warning "Le processus est encore ouvert (UI active ?). Fermez l'application pour poursuivre."
    while (-not $p.HasExited) { Start-Sleep -Milliseconds 200 }
  }
  $out = $p.StandardOutput.ReadToEnd()
  $err = $p.StandardError.ReadToEnd()
  Set-Content $so $out -Encoding UTF8
  Set-Content $se $err -Encoding UTF8
  return @{ Code = $p.ExitCode; Out = $out; Err = $err; OutPath = $so; ErrPath = $se }
}

# Préparation
$Python = Resolve-Python $PythonPath
 $envVars = Read-EnvFile
 # Preserve original app/.env contents so we can restore passwords for Case C
 $origEnv = $null
 if (Test-Path "app/.env") {
   try { $origEnv = Get-Content "app/.env" -Raw } catch { $origEnv = $null }
 }
if ([string]::IsNullOrWhiteSpace($ValidDsn)) {
  if ($envVars.ContainsKey("PAYROLL_DSN")) { $ValidDsn = $envVars["PAYROLL_DSN"] }
}

New-Item -ItemType Directory -Force -Path "./_dbtest" | Out-Null

# --- Cas A : DSN absent ---
# If a previous app/.env.off exists remove it first to avoid Move-Item error
if (Test-Path "app/.env.off") { Remove-Item "app/.env.off" -Force }
if (Test-Path "app/.env") { Move-Item "app/.env" "app/.env.off" -Force }
Write-Host "`n=== CAS A : DSN ABSENT ==="
$resA = Run-App -Python $Python -Entry $Entry -LogBase "./_dbtest/caseA" -TimeoutSec $TimeoutSec
$passA = ($resA.Code -ne 0) -and ($resA.Out + $resA.Err) -notmatch "SUCCESS:\s*Connexion PostgreSQL"
Write-Host ("Résultat A : " + ($(if($passA){"PASS"}else{"FAIL"})) + " (exit={0})" -f $resA.Code)

# --- Cas B : DSN invalide ---
if ($origEnv) { Set-Content "app/.env" $origEnv -Encoding UTF8 } else { Set-Content "app/.env" "" -Encoding UTF8 }
$envVars = Read-EnvFile
if (-not $envVars.ContainsKey("PAYROLL_DSN")) {
  if ([string]::IsNullOrWhiteSpace($ValidDsn)) {
    Write-Error "PAYROLL_DSN introuvable et -ValidDsn non fourni. Abandon."
    exit 1
  } else {
    $envVars["PAYROLL_DSN"] = $ValidDsn
  }
}
$bad = Make-InvalidDsn $envVars["PAYROLL_DSN"]
$envVars["PAYROLL_DSN"] = $bad
Write-EnvFile -Vars $envVars

Write-Host "`n=== CAS B : DSN INVALIDE ==="
$resB = Run-App -Python $Python -Entry $Entry -LogBase "./_dbtest/caseB" -TimeoutSec $TimeoutSec
$passB = ($resB.Code -ne 0) -and ($resB.Out + $resB.Err) -notmatch "SUCCESS:\s*Connexion PostgreSQL"
Write-Host ("DSN invalide utilisé : {0}" -f (Mask-DSN $bad))
Write-Host ("Résultat B : " + ($(if($passB){"PASS"}else{"FAIL"})) + " (exit={0})" -f $resB.Code)

# --- Cas C : DSN valide ---
if ($origEnv) { Set-Content "app/.env" $origEnv -Encoding UTF8 }
if (-not (Test-Path "app/.env")) {
  if ([string]::IsNullOrWhiteSpace($ValidDsn)) {
    Write-Error "Aucun .env et -ValidDsn non fourni pour le Cas C."
    exit 1
  } else {
    Set-Content "app/.env" ("PAYROLL_DSN={0}`nAPP_ENV=development" -f $ValidDsn) -Encoding UTF8
  }
}

Write-Host "`n=== CAS C : DSN VALIDE ==="
# Start the app, then ask the small check script whether DB is connected using the same provider logic.
$resC = Run-App -Python $Python -Entry $Entry -LogBase "./_dbtest/caseC" -TimeoutSec $TimeoutSec

# Run the structured check script which returns JSON {ok:bool, user, db, error}
$checkScript = "./app/_cleanup_report/check_db_conn.py"
$dsnVal = (Read-EnvFile)["PAYROLL_DSN"]
$checkOut = & $Python $checkScript --dsn "$dsnVal" 2>&1
Write-Host $checkOut

$passC = $false
try {
  $json = $checkOut | Out-String | ConvertFrom-Json -ErrorAction Stop
  if ($json.ok -eq $true) { $passC = $true }
} catch {
  # If JSON parse failed, fallback to naive text search for compatibility
  if (($resC.Out + $resC.Err) -match "SUCCESS: Connexion PostgreSQL") { $passC = $true }
}

Write-Host ("DSN valide utilisé : {0}" -f (Mask-DSN ((Read-EnvFile)["PAYROLL_DSN"])))
Write-Host ("Résultat C : " + ($(if($passC){"PASS"}else{"FAIL"})) + " (exit={0})" -f $resC.Code)

# Restauration env
if ($origEnv) { Set-Content "app/.env" $origEnv -Encoding UTF8 }
if (Test-Path "app/.env.off") { Move-Item "app/.env.off" "app/.env" -Force }

Write-Host "`n=== RÉSUMÉ ==="
"{0,-8} {1}" -f "Cas","Statut"
"{0,-8} {1}" -f "A",($(if($passA){"PASS"}else{"FAIL"}))
"{0,-8} {1}" -f "B",($(if($passB){"PASS"}else{"FAIL"}))
"{0,-8} {1}" -f "C",($(if($passC){"PASS"}else{"FAIL"}))
Write-Host "Logs : _dbtest\caseA.out/err.txt, caseB.out/err.txt, caseC.out/err.txt"

# --- CAS KPI : Vérification des KPIs via la base PostgreSQL (pas d'artefacts locaux)
Write-Host "`n=== CAS KPI : Vérification KPIs depuis la base PostgreSQL ==="
$kpiScript = "./app/_cleanup_report/query_kpi_db.py"

$passKPI = $false
try {
  $kpiOut = & $Python $kpiScript 2>&1
  Write-Host $kpiOut
  $kpi = $null
  try {
    $kpi = $kpiOut | Out-String | ConvertFrom-Json -ErrorAction Stop
  } catch {
    Write-Warning "Impossible d'analyser la sortie JSON du script KPI : $_"
    $kpi = $null
  }
} catch {
  Write-Warning "Échec exécution script KPI: $_"
  $kpi = $null
}

# Valeurs attendues (valeurs validées par l'utilisateur)
$expected_total_net = 538402.22
$expected_nb_employees = 295
$expected_avg = 1825.09
$tol = 0.01

if ($kpi -ne $null -and $kpi.PSObject.Properties.Name -contains 'total_net') {
  $diff_total = [math]::Abs([double]$kpi.total_net - [double]$expected_total_net)
  $diff_avg = [math]::Abs([double]$kpi.avg_net_per_employee - [double]$expected_avg)

  $passTotal = ($diff_total -le $tol)
  $passEmp = ($kpi.nb_employees -eq $expected_nb_employees)
  $passAvg = ($diff_avg -le $tol)

  if ($passTotal -and $passEmp -and $passAvg) {
    Write-Host "KPI Check (DB): PASS"
    $passKPI = $true
  } else {
    Write-Host "KPI Check (DB): FAIL"
    Write-Host " Expected total_net: $expected_total_net, got: $($kpi.total_net) (diff:$diff_total)"
    Write-Host " Expected nb_employees: $expected_nb_employees, got: $($kpi.nb_employees)"
    Write-Host " Expected avg: $expected_avg, got: $($kpi.avg_net_per_employee) (diff:$diff_avg)"
    $passKPI = $false
  }
} else {
  Write-Warning "KPI DB query failed or returned unexpected output. See script output above."
  $passKPI = $false
}

Write-Host "`n=== RÉSUMÉ FINAL ==="
"{0,-8} {1}" -f "Cas","Statut"
"{0,-8} {1}" -f "A",($(if($passA){"PASS"}else{"FAIL"}))
"{0,-8} {1}" -f "B",($(if($passB){"PASS"}else{"FAIL"}))
"{0,-8} {1}" -f "C",($(if($passC){"PASS"}else{"FAIL"}))
"{0,-8} {1}" -f "KPI",($(if($passKPI){"PASS"}else{"FAIL"}))

# Exit non-zero if any check failed
if (-not ($passA -and $passB -and $passC -and $passKPI)) {
  Write-Error "Un ou plusieurs tests d'acceptance ont échoué. Voir logs et kpi_summary.json"
  exit 1
} else {
  Write-Host "Tous les tests d'acceptance sont PASS"
  exit 0
}
