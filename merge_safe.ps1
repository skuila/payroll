# Merge safe : merge origin/main into ruff/fixes and push (no force)
# PowerShell adaptation

$ErrorActionPreference = "Stop"

Write-Host "-> Merge sûr : origin/main ? ruff/fixes" -ForegroundColor Cyan
Write-Host ""

# Vérifications
try {
    git rev-parse --is-inside-work-tree 2>&1 | Out-Null
} catch {
    Write-Host "Erreur : ce répertoire n'est pas un dépôt git. Place-toi à la racine du repo." -ForegroundColor Red
    exit 1
}

# Pas de changements non committés
$STATUS = git status --porcelain
if ($STATUS) {
    Write-Host "Il y a des modifications non committées. Commits/ stash/ reset avant de continuer." -ForegroundColor Red
    git status --porcelain
    exit 1
}

# Récupérer le distant
Write-Host "Récupération des changements depuis origin..." -ForegroundColor Yellow
try {
    git fetch origin 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git fetch a échoué"
    }
} catch {
    Write-Host "git fetch a échoué: $_" -ForegroundColor Red
    exit 1
}

# Basculer sur la branche
$branchExists = git show-ref --verify --quiet refs/heads/ruff/fixes
if ($LASTEXITCODE -eq 0) {
    Write-Host "Checkout de la branche ruff/fixes..." -ForegroundColor Yellow
    git checkout ruff/fixes
} else {
    Write-Host "La branche ruff/fixes n'existe pas localement : création..." -ForegroundColor Yellow
    git checkout -b ruff/fixes
}

Write-Host "`nMerge en cours..." -ForegroundColor Cyan
$MERGE_OUTPUT = git merge origin/main 2>&1 | Out-String
$MERGE_EXIT = $LASTEXITCODE

if ($MERGE_EXIT -eq 0) {
    Write-Host "Merge réussi. Poussée vers origin..." -ForegroundColor Green
    git push origin ruff/fixes
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nPush OK. Maintenant ouvre la PR :" -ForegroundColor Green
        Write-Host "https://github.com/skuila/payroll/pull/new/ruff/fixes?expand=1" -ForegroundColor Cyan
    } else {
        Write-Host "Push échoué" -ForegroundColor Red
        exit 1
    }
    exit 0
} else {
    Write-Host "Merge échoué (exit code $MERGE_EXIT). Sortie :" -ForegroundColor Red
    Write-Host "------------------------------------------------"
    Write-Host $MERGE_OUTPUT
    Write-Host "------------------------------------------------"
    
    # Cas d'histoires sans ancêtre commun
    if ($MERGE_OUTPUT -match "refusing to merge unrelated histories") {
        Write-Host ""
        Write-Host "Git a refusé la fusion : histoires non reliées." -ForegroundColor Yellow
        Write-Host "Si tu veux forcer la fusion des histoires, utilise :" -ForegroundColor Yellow
        Write-Host "  git merge origin/main --allow-unrelated-histories" -ForegroundColor White
        exit 2
    }
    
    # Conflits ?
    $conflicts = git ls-files -u
    if ($conflicts) {
        Write-Host ""
        Write-Host "Conflits détectés. Fichiers en conflit :" -ForegroundColor Yellow
        git diff --name-only --diff-filter=U
        Write-Host ""
        Write-Host "Pour résoudre les conflits :" -ForegroundColor Cyan
        Write-Host "1) Ouvre chaque fichier listé et recherche les marqueurs <<<<<<< ======= >>>>>>>" -ForegroundColor White
        Write-Host "2) Corrige le code (choisir la partie à garder), supprime les marqueurs" -ForegroundColor White
        Write-Host "3) git add <fichier>" -ForegroundColor White
        Write-Host "4) Quand tous résolus : git commit" -ForegroundColor White
        Write-Host "5) git push origin ruff/fixes" -ForegroundColor White
        exit 3
    }
    
    Write-Host "Échec inconnu du merge. Inspecte la sortie ci-dessus." -ForegroundColor Red
    exit 4
}
