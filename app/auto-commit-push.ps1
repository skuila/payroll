# Script PowerShell pour auto-commit-push
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Configuration
$TYPE = "fix"
$SCOPE = "importer"
$TITLE_SHORT = "corriger erreurs AmbiguousParameter import"
$FILES_MODIFIED = @("providers/postgres_provider.py", "services/import_service_complete.py")
$STRATEGY = "merge"

# Génération du nom de branche
$SLUG = $TITLE_SHORT.ToLower() -replace '[^a-z0-9]', '-' -replace '-+', '-' -replace '^-|-$', ''
$TIMESTAMP = Get-Date -Format "yyyyMMddHHmmss"
$BRANCH = "auto/${TYPE}-${SCOPE}-${SLUG}-${TIMESTAMP}"

Write-Host "=========================================="
Write-Host "AUTO-COMMIT-PUSH SCRIPT"
Write-Host "=========================================="
Write-Host "Branche: $BRANCH"
Write-Host ""

# Vérification des outils requis
function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction Stop
}

Write-Host "🔍 Vérification des outils..."
try {
    Test-Command "git"
    Test-Command "gh"
    Test-Command "black"
    Test-Command "isort"
    Test-Command "ruff"
    Test-Command "mypy"
    Test-Command "pytest"
    Test-Command "bandit"
    Test-Command "safety"
    Write-Host "✅ Tous les outils sont disponibles"
} catch {
    Write-Host "❌ ERREUR: $_"
    exit 1
}
Write-Host ""

# Synchronisation avec origin/main
Write-Host "🌿 Synchronisation avec origin/main..."
git fetch origin
if ($LASTEXITCODE -ne 0) { exit 1 }

if ($STRATEGY -eq "merge") {
    git merge origin/main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Conflit lors du merge avec origin/main"
        exit 1
    }
} else {
    git rebase origin/main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur lors du rebase avec origin/main"
        exit 1
    }
}
Write-Host "✅ Synchronisé avec origin/main"
Write-Host ""

# Exécution des checks
Write-Host "🔧 Exécution des checks de qualité..."
$FAILED_CHECKS = @()

Write-Host "  → isort..."
isort --check-only --diff $FILES_MODIFIED 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    isort $FILES_MODIFIED
    if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "isort" }
}

Write-Host "  → black..."
black --check --diff $FILES_MODIFIED 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    black $FILES_MODIFIED
    if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "black" }
}

Write-Host "  → ruff format..."
ruff format $FILES_MODIFIED
if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "ruff-format" }

Write-Host "  → ruff check..."
ruff check --fix $FILES_MODIFIED
if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "ruff-check" }

Write-Host "  → mypy..."
mypy $FILES_MODIFIED
if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "mypy" }

Write-Host "  → pytest..."
pytest -v
if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "pytest" }

Write-Host "  → bandit..."
bandit -r app -f json -o /tmp/bandit-report.json
if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "bandit" }

Write-Host "  → safety..."
safety check --json
if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "safety" }

if (Test-Path "scripts/forbid_direct_db_connect.py") {
    Write-Host "  → validation DB..."
    python scripts/forbid_direct_db_connect.py
    if ($LASTEXITCODE -ne 0) { $FAILED_CHECKS += "db-validate" }
}

if ($FAILED_CHECKS.Count -ne 0) {
    Write-Host "❌ ÉCHEC des checks suivants: $($FAILED_CHECKS -join ', ')"
    exit 1
}

Write-Host "✅ Tous les checks sont passés"
Write-Host ""

# Commit
Write-Host "📝 Commit des changements..."
git add $FILES_MODIFIED
if ($LASTEXITCODE -ne 0) { exit 1 }

$COMMIT_MSG = @"
fix(importer): corriger erreurs AmbiguousParameter import

Pourquoi : Correction des erreurs PostgreSQL AmbiguousParameter dans get_table() et _upsert_employees() pour permettre l'import de fichiers Excel.

Ce qui a été changé :
- Correction du cast pay_date dans get_table() pour éviter l'ambiguïté de type
- Refactorisation de _upsert_employees() pour utiliser employee_key au lieu de matricule
- Alignement avec le schéma standard de core.employees

Checklist :
- [x] black / isort
- [x] ruff
- [x] mypy
- [x] pytest
- [x] bandit
- [x] safety

Fichiers :
- providers/postgres_provider.py
- services/import_service_complete.py
"@

git commit -m $COMMIT_MSG
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du commit (peut-être aucun changement à committer)"
    exit 1
}
Write-Host "✅ Commit créé"
Write-Host ""

# Push
Write-Host "🚀 Push vers origin..."
git push --set-upstream origin (git branch --show-current)
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du push"
    exit 1
}
Write-Host "✅ Branche poussée"
Write-Host ""

# Création de la PR
Write-Host "📋 Création de la PR draft..."
$PR_BODY = @"
## Description

Correction des erreurs PostgreSQL AmbiguousParameter dans get_table() et _upsert_employees() pour permettre l'import de fichiers Excel.

## Checklist

- [x] black / isort
- [x] ruff
- [x] mypy
- [x] pytest
- [x] bandit
- [x] safety

## Fichiers modifiés

- providers/postgres_provider.py
- services/import_service_complete.py
"@

$PR_URL = gh pr create --draft --title "WIP: corriger erreurs AmbiguousParameter import" --body $PR_BODY --label autogenerated 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors de la création de la PR"
    exit 1
}

Write-Host "✅ PR créée: $PR_URL"
Write-Host ""
Write-Host "=========================================="
Write-Host "✅ TERMINÉ"
Write-Host "=========================================="
Write-Host "Vérifier la PR sur GitHub et merger manuellement:"
Write-Host "$PR_URL"

