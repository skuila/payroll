# ============================================================================
# Script PowerShell - Exécution Migration Référentiel Employés
# Windows PowerShell 5.1+
# ============================================================================

param(
    [string]$PsqlPath = "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    [string]$User = "payroll_app",
    [string]$Database = "payroll_db",
    [string]$Host = "localhost",
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "MIGRATION RÉFÉRENTIEL EMPLOYÉS - EXÉCUTION AUTOMATISÉE" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PHASE 0: VÉRIFICATIONS
# ============================================================================

Write-Host "Phase 0: Vérifications préalables..." -ForegroundColor Yellow

# Vérifier psql
if (-not (Test-Path $PsqlPath)) {
    Write-Host "❌ psql non trouvé: $PsqlPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "  1. Installer PostgreSQL (https://www.postgresql.org/download/windows/)"
    Write-Host "  2. Spécifier le chemin: .\execute_migration.ps1 -PsqlPath 'C:\...\psql.exe'"
    Write-Host ""
    exit 1
}

Write-Host "  ✓ psql trouvé: $PsqlPath" -ForegroundColor Green

# Vérifier fichiers migration
$RequiredFiles = @(
    "01_ddl_referentiel.sql",
    "02_migrate_to_referentiel.sql",
    "03_tests_validation.sql"
)

foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "❌ Fichier manquant: $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host "  ✓ Tous les fichiers SQL présents" -ForegroundColor Green
Write-Host ""

# ============================================================================
# PHASE 1: BACKUP
# ============================================================================

if (-not $SkipBackup) {
    Write-Host "Phase 1: Backup base de données..." -ForegroundColor Yellow
    Write-Host "  Utilisation du script Python..." -ForegroundColor Gray
    
    python backup_database.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Backup échoué" -ForegroundColor Red
        $response = Read-Host "Continuer sans backup ? (o/n)"
        if ($response -ne 'o') {
            Write-Host "Migration annulée par sécurité" -ForegroundColor Yellow
            exit 1
        }
    }
    
    Write-Host ""
}

# ============================================================================
# PHASE 2: CRÉATION STRUCTURES
# ============================================================================

Write-Host "Phase 2: Création des structures (DDL)..." -ForegroundColor Yellow

$env:PGPASSWORD = $env:PAYROLL_DB_PASSWORD

& $PsqlPath -h $Host -U $User -d $Database -f "01_ddl_referentiel.sql" 2>&1 | Tee-Object -Variable ddlOutput

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ DDL échoué" -ForegroundColor Red
    Write-Host $ddlOutput
    exit 1
}

Write-Host "  ✓ Structures créées avec succès" -ForegroundColor Green
Write-Host ""

# ============================================================================
# PHASE 3: MIGRATION DONNÉES
# ============================================================================

Write-Host "Phase 3: Migration des données..." -ForegroundColor Yellow
Write-Host "  (Ceci peut prendre 5-15 minutes...)" -ForegroundColor Gray

& $PsqlPath -h $Host -U $User -d $Database -f "02_migrate_to_referentiel.sql" 2>&1 | Tee-Object -Variable migOutput

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migration échouée" -ForegroundColor Red
    Write-Host $migOutput
    exit 1
}

# Vérifier succès dans output
if ($migOutput -match "MIGRATION TERMINÉE AVEC SUCCÈS") {
    Write-Host "  ✓ Migration complétée avec succès" -ForegroundColor Green
    
    # Extraire statistiques
    if ($migOutput -match "Employés\s+:\s+(\d+)") {
        $nbEmployes = $matches[1]
        Write-Host "  → $nbEmployes employés créés" -ForegroundColor Cyan
    }
    
    if ($migOutput -match "Transactions\s+:\s+(\d+)") {
        $nbTransactions = $matches[1]
        Write-Host "  → $nbTransactions transactions insérées" -ForegroundColor Cyan
    }
} else {
    Write-Host "⚠️  Migration terminée mais statut incertain" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# PHASE 4: TESTS VALIDATION
# ============================================================================

Write-Host "Phase 4: Tests de validation..." -ForegroundColor Yellow

& $PsqlPath -h $Host -U $User -d $Database -f "03_tests_validation.sql" 2>&1 | Tee-Object -Variable testOutput

# Vérifier résultats clés
$nouveauComptage = 0
if ($testOutput -match "Nouveau comptage 2025-08.*\|\s+(\d+)") {
    $nouveauComptage = [int]$matches[1]
}

$orphelins = -1
if ($testOutput -match "Transactions orphelines.*\|\s+(\d+)") {
    $orphelins = [int]$matches[1]
}

Write-Host ""
Write-Host "  Résultats clés:" -ForegroundColor Cyan
Write-Host "    Nouveau comptage 2025-08 : $nouveauComptage employés" -ForegroundColor $(if ($nouveauComptage -eq 295) { "Green" } else { "Yellow" })
Write-Host "    Orphelins                : $orphelins" -ForegroundColor $(if ($orphelins -eq 0) { "Green" } else { "Red" })

if ($nouveauComptage -ne 295) {
    Write-Host "  ⚠️  Comptage inattendu (attendu: 295)" -ForegroundColor Yellow
}

if ($orphelins -gt 0) {
    Write-Host "  ❌ Orphelins détectés! Vérifier logs" -ForegroundColor Red
}

Write-Host ""

# ============================================================================
# PHASE 5: TESTS PYTHON
# ============================================================================

Write-Host "Phase 5: Tests Python (KPI)..." -ForegroundColor Yellow

python test_kpi_regression.py 2>&1 | Tee-Object -Variable pyTestOutput

if ($pyTestOutput -match "TOUS LES TESTS RÉUSSIS") {
    Write-Host "  ✓ Tous les tests Python réussis" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Certains tests Python ont échoué" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "MIGRATION TERMINÉE" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

if ($nouveauComptage -eq 295 -and $orphelins -eq 0) {
    Write-Host "✅ SUCCÈS - Migration validée" -ForegroundColor Green
    Write-Host ""
    Write-Host "Prochaines étapes:" -ForegroundColor Yellow
    Write-Host "  1. Appliquer patch Python (voir 04_patch_python.md)"
    Write-Host "  2. Tester l'interface utilisateur"
    Write-Host "  3. Vérifier carte 'Employés actifs' = 295"
    Write-Host ""
} else {
    Write-Host "⚠️  ATTENTION - Vérifier les résultats" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Actions recommandées:" -ForegroundColor Yellow
    Write-Host "  1. Consulter les logs de migration"
    Write-Host "  2. Vérifier les tests SQL (03_tests_validation.sql)"
    Write-Host "  3. Contacter support si nécessaire"
    Write-Host ""
}

Write-Host "Logs sauvegardés dans PowerShell transcript" -ForegroundColor Gray
Write-Host "============================================================================" -ForegroundColor Cyan

