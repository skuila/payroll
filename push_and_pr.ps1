# PROMPT CURSOR — Push branch ruff/fixes et créer PR (FR)
# PowerShell adaptation

$ErrorActionPreference = "Stop"

# --- CONFIG ---
$REPO_URL = "https://github.com/skuila/payroll.git"
$BRANCH = "ruff/fixes"
$PR_TITLE = "Fix: Ruff issues (auto fixes + safe edits)"
$PR_BODY = @"
Applied ruff --fix and safe automated edits (split imports, bare except -> except Exception as _exc).

Temporary changes:
- pyproject.toml: exclude archive/legacy_non_standard/** and per-file-ignores for app/ui/*.py
- tools/safe_fixes.py created and backups (*.bak) saved.

Remaining manual work: see ruff-remaining.txt (E401, E722, F841). Priority files: app/payroll_app_qt_Version4.py, app/ui/*
"@

Write-Host "=== Push branch ruff/fixes et créer PR ===" -ForegroundColor Cyan
Write-Host ""

# --- Pré-vérifications ---
try {
    git rev-parse --is-inside-work-tree 2>&1 | Out-Null
    Write-Host "Repository root détecté." -ForegroundColor Green
} catch {
    Write-Host "Erreur : ce répertoire n'est pas un dépôt git." -ForegroundColor Red
    exit 1
}

# Vérifier branche courante
$CURRENT_BRANCH = git rev-parse --abbrev-ref HEAD
Write-Host "Branche courante: $CURRENT_BRANCH"

# Assurer que la branche cible existe localement
$branchExists = git show-ref --verify --quiet "refs/heads/$BRANCH"
if ($LASTEXITCODE -eq 0) {
    Write-Host "La branche locale '$BRANCH' existe." -ForegroundColor Green
} else {
    Write-Host "La branche '$BRANCH' n'existe pas localement. Création et checkout..." -ForegroundColor Yellow
    git checkout -b $BRANCH
}

# S'assurer qu'on est sur la branche ruff/fixes
git checkout $BRANCH

# Vérifier l'état de l'arbre de travail
$STATUS = git status --porcelain
if ($STATUS) {
    Write-Host "Il y a des modifications non committées dans l'espace de travail :" -ForegroundColor Yellow
    git status --porcelain
    Write-Host "=> Merci de committer (ou stasher) ces modifications avant de pousser. Abort." -ForegroundColor Red
    exit 1
}

# Vérifier le dernier commit sur la branche
Write-Host "`nDernier commit sur $BRANCH :" -ForegroundColor Cyan
git --no-pager log -1 --oneline

# --- Configurer remote origin si nécessaire ---
$remotes = git remote
if ($remotes -contains "origin") {
    $CURRENT_URL = git remote get-url origin
    Write-Host "Remote 'origin' existe déjà: $CURRENT_URL"
    if ($CURRENT_URL -ne $REPO_URL) {
        Write-Host "Remplacement de l'URL 'origin' par $REPO_URL" -ForegroundColor Yellow
        git remote set-url origin $REPO_URL
    } else {
        Write-Host "Origin déjà correctement configuré." -ForegroundColor Green
    }
} else {
    Write-Host "Ajout du remote origin -> $REPO_URL" -ForegroundColor Yellow
    git remote add origin $REPO_URL
}

# --- Push de la branche ---
Write-Host "`nPoussée de la branche $BRANCH vers origin..." -ForegroundColor Cyan
try {
    git push -u origin $BRANCH 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Push réussi." -ForegroundColor Green
    } else {
        throw "Push failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "Push échoué. Vérifie l'authentification (token ou gh auth). Aborting." -ForegroundColor Red
    Write-Host "Erreur: $_" -ForegroundColor Red
    exit 1
}

# --- Création de la PR (via gh si dispo) ---
$ghAvailable = Get-Command gh -ErrorAction SilentlyContinue
if ($ghAvailable) {
    Write-Host "`ngh CLI détecté. Vérification d'authentification..." -ForegroundColor Cyan
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "gh n'est pas authentifié. Lancement de gh auth login (interactif)..." -ForegroundColor Yellow
        gh auth login
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Authentification gh failed" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "Création de la Pull Request avec gh..." -ForegroundColor Cyan
    try {
        $PR_URL = gh pr create --title $PR_TITLE --body $PR_BODY --base main --head $BRANCH --assignee @me --reviewer @me 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PR créée : $PR_URL" -ForegroundColor Green
        } else {
            # Tenter sans assign/reviewer
            gh pr create --title $PR_TITLE --body $PR_BODY --base main --head $BRANCH
            Write-Host "PR créée via gh." -ForegroundColor Green
        }
    } catch {
        Write-Host "Erreur lors de la création de la PR: $_" -ForegroundColor Yellow
    }
} else {
    # gh absent : afficher URL de comparaison
    $ORIGIN_URL = git remote get-url origin
    # Extraire owner/repo
    if ($ORIGIN_URL -match "^git@[^:]+:([^/]+/[^.]+)(\.git)?$") {
        $OWNER_REPO = $matches[1]
    } elseif ($ORIGIN_URL -match "https?://[^/]+/([^/]+/[^.]+)(\.git)?") {
        $OWNER_REPO = $matches[1]
    } else {
        $OWNER_REPO = "skuila/payroll"
    }
    $PR_URL = "https://github.com/${OWNER_REPO}/compare/main...${BRANCH}?expand=1"
    Write-Host "`ngh CLI non trouvé. Ouvre manuellement l'URL suivante dans ton navigateur pour créer la PR:" -ForegroundColor Yellow
    Write-Host $PR_URL -ForegroundColor Cyan
}

# --- Liste des fichiers modifiés récents pour revue ---
Write-Host "`nFichiers modifiés dans le dernier commit (top 100) :" -ForegroundColor Cyan
git --no-pager diff --name-only HEAD~1 HEAD 2>&1 | Select-Object -First 100

Write-Host "`nFichiers listés dans ruff-remaining.txt (top 20) :" -ForegroundColor Cyan
if (Test-Path "ruff-remaining.txt") {
    Get-Content "ruff-remaining.txt" | ForEach-Object { $_.Split()[0] } | Group-Object | Sort-Object Count -Descending | Select-Object -First 20 | Format-Table Count, Name -AutoSize
} else {
    Write-Host "ruff-remaining.txt introuvable dans le répertoire courant." -ForegroundColor Yellow
}

Write-Host "`nTerminé. Si la PR n'a pas été créée automatiquement, ouvre l'URL indiquée et crée la PR manuellement." -ForegroundColor Green
Write-Host "Vérifie ensuite les fichiers prioritaires listés ci-dessus." -ForegroundColor Green
