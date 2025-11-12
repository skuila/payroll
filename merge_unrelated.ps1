# Merge allowing unrelated histories (use only if asked)
# PowerShell adaptation

$ErrorActionPreference = "Stop"

Write-Host "-> Merge AVANCÉ : origin/main --> ruff/fixes avec --allow-unrelated-histories" -ForegroundColor Cyan
Write-Host ""

# Vérifications
try {
    git rev-parse --is-inside-work-tree 2>&1 | Out-Null
} catch {
    Write-Host "Not a git repo. Aborting." -ForegroundColor Red
    exit 1
}

# Pas de changements non committés
$STATUS = git status --porcelain
if ($STATUS) {
    Write-Host "Uncommitted changes found. Commit or stash first." -ForegroundColor Red
    git status --porcelain
    exit 1
}

# Fetch
Write-Host "Fetching from origin..." -ForegroundColor Yellow
try {
    git fetch origin 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "git fetch failed"
    }
} catch {
    Write-Host "git fetch failed: $_" -ForegroundColor Red
    exit 1
}

# Checkout branche
$branchExists = git show-ref --verify --quiet refs/heads/ruff/fixes
if ($LASTEXITCODE -eq 0) {
    Write-Host "Checkout ruff/fixes..." -ForegroundColor Yellow
    git checkout ruff/fixes
} else {
    Write-Host "Creating ruff/fixes..." -ForegroundColor Yellow
    git checkout -b ruff/fixes
}

Write-Host "`nMerging with --allow-unrelated-histories..." -ForegroundColor Cyan
$MERGE_OUTPUT = git merge origin/main --allow-unrelated-histories 2>&1 | Out-String
$MERGE_EXIT = $LASTEXITCODE

if ($MERGE_EXIT -eq 0) {
    Write-Host "Merge (allow-unrelated-histories) succeeded. Pushing..." -ForegroundColor Green
    git push origin ruff/fixes
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nPush OK. Open PR:" -ForegroundColor Green
        Write-Host "https://github.com/skuila/payroll/pull/new/ruff/fixes?expand=1" -ForegroundColor Cyan
    }
    exit 0
} else {
    Write-Host "Merge failed. Output:" -ForegroundColor Red
    Write-Host $MERGE_OUTPUT
    
    # Check conflicts
    $conflicts = git ls-files -u
    if ($conflicts) {
        Write-Host "`nConflicts detected:" -ForegroundColor Yellow
        git diff --name-only --diff-filter=U
        Write-Host "`nResolve conflicts:" -ForegroundColor Cyan
        Write-Host "1) Open each conflicted file" -ForegroundColor White
        Write-Host "2) Search for <<<<<<< ======= >>>>>>>" -ForegroundColor White
        Write-Host "3) Choose which code to keep, remove markers" -ForegroundColor White
        Write-Host "4) git add <file>" -ForegroundColor White
        Write-Host "5) git commit" -ForegroundColor White
        Write-Host "6) git push origin ruff/fixes" -ForegroundColor White
        exit 3
    }
    exit 2
}
