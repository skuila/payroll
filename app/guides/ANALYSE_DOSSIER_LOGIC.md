# Analyse du Dossier `logic/`

## Vue d'ensemble

Le dossier `logic/` contient des modules de **logique métier** pour l'analyse de la paie. Ces modules fournissent des fonctions de calcul, d'audit, de génération de rapports et d'optimisation de base de données.

**Statut global** : ⚠️ **PARTIELLEMENT UTILISÉ** - Certains modules sont actifs, d'autres sont obsolètes ou non utilisés dans l'application actuelle (Tabler UI).

---

## Fichiers du Dossier

### 1. `__init__.py`
**Rôle** : Fichier d'initialisation Python (marque le dossier comme package)  
**Utilisation** : ✅ Utilisé (nécessaire pour les imports)  
**Action** : **CONSERVER**

---

### 2. `analytics.py` ⚠️
**Rôle** : Calcul des KPIs, détection d'anomalies et comparaisons pour le bilan post-import  
**Fonctions principales** :
- `compute_period_summary()` : Résumé complet de la dernière période
- `_compute_kpis()` : Calcul des KPIs de base (net total, brut, déductions, effectifs)
- `_detect_all_anomalies()` : Détection d'anomalies (nets négatifs, inactifs avec gains, codes sensibles, etc.)
- `_compare_with_previous_period()` : Comparaison avec période précédente

**Utilisation** : ❌ **NON UTILISÉ** dans l'application actuelle  
**Raison** : L'application utilise maintenant `providers/postgres_provider.py` et `api/routes/kpi.py` pour les KPIs  
**Action** : **ARCHIVER** (code obsolète mais peut servir de référence)

---

### 3. `audit.py` ✅
**Rôle** : Audit de base des données de paie (détection d'anomalies)  
**Fonctions principales** :
- `run_basic_audit(period)` : Audit rapide d'une période
- `compare_periods(p1, p2)` : Comparaison entre deux périodes
- `_detect_nets_negatifs()` : Détecte les employés avec net négatif
- `_detect_majuscules()` : Détecte les noms en MAJUSCULES (inactifs)
- `_detect_codes_sensibles()` : Détecte les codes de paie sensibles

**Utilisation** : ✅ **UTILISÉ** dans :
- `ui/menus/analysis_menu.py` : Menu d'analyse
- `ui/overlays/period_summary_card.py` : Carte de résumé de période
- `agent/standalone_app.py` : Application agent IA
- `agent/payroll_agent.py` : Agent IA de paie

**Action** : **CONSERVER** (module actif)

---

### 4. `db_optimizer.py` ⚠️
**Rôle** : Optimisation de la base de données PostgreSQL (vérification d'index, cache KPI)  
**Fonctions principales** :
- `create_indexes()` : Vérifie les index PostgreSQL existants
- `create_cache_table()` : Vérifie l'existence de `payroll.kpi_snapshot`
- `save_kpi_cache()` : Sauvegarde les KPI dans le cache
- `get_kpi_cache()` : Récupère les KPI depuis le cache
- `invalidate_cache()` : Invalide le cache
- `optimize_database()` : Lance l'optimisation complète

**Utilisation** : ❌ **NON UTILISÉ** dans l'application actuelle  
**Raison** : L'optimisation est gérée directement par les migrations SQL et les providers  
**Action** : **ARCHIVER** (peut être utile pour maintenance manuelle)

---

### 5. `formatting.py` ✅
**Rôle** : Fonctions utilitaires de formatage (nombres, dates, périodes)  
**Fonctions principales** :
- `_parse_number_safe(value)` : Parse un nombre de manière sécurisée
- `_fmt_money(value)` : Formate un montant en dollars
- `_normalize_period(date_like)` : Normalise une période (date → format standard)

**Utilisation** : ✅ **UTILISÉ** dans :
- `logic/audit.py` : Formatage des données d'audit
- `logic/reports.py` : Formatage des rapports
- `ui/overlays/period_summary_card.py` : Formatage des périodes

**Action** : **CONSERVER** (module utilitaire actif)

---

### 6. `insights.py` ✅
**Rôle** : Génération d'insights textuels à partir du résumé analytique  
**Fonctions principales** :
- `generate_insights(summary)` : Génère une liste de phrases d'analyse lisibles
- `_insight_kpis()` : Insights sur les KPIs
- `_insight_anomalies()` : Insights sur les anomalies
- `_insight_comparaison()` : Insights sur la comparaison avec période précédente

**Utilisation** : ✅ **UTILISÉ** dans :
- `ui/overlays/period_summary_card.py` : Génération d'insights pour la carte de résumé

**Action** : **CONSERVER** (module actif)

---

### 7. `kpi_engine.py` ⚠️
**Rôle** : Moteur de calcul des KPI avancés (financiers, RH, tendances, alertes)  
**Fonctions principales** :
- `masse_salariale()` : Calcule la masse salariale totale
- `salaire_net()` : Calcule le salaire net total
- `deductions_totales()` : Calcule les déductions totales
- `effectifs()` : Calcule le nombre d'employés actifs
- `taux_rotation()` : Calcule le taux de rotation
- `heures_supplementaires()` : Calcule le coût des heures supplémentaires
- `calculate_all_kpis()` : Calcule tous les KPI pour une période
- `get_kpi_alerts()` : Récupère toutes les alertes KPI

**Utilisation** : ⚠️ **PARTIELLEMENT UTILISÉ** dans :
- `ui/data_provider.py` : Utilisé pour certains calculs de KPI (mais l'application principale utilise `providers/postgres_provider.py`)

**Raison** : L'application actuelle (Tabler UI) utilise principalement `providers/postgres_provider.py` et `api/routes/kpi.py` pour les KPIs  
**Action** : **ARCHIVER** (code obsolète mais peut servir de référence pour calculs avancés)

---

### 8. `metrics.py` ✅
**Rôle** : Chargement robuste et colonnes canoniques pour les audits  
**Fonctions principales** :
- `_load_df()` : Charge les données depuis PostgreSQL (`payroll.imported_payroll_master`)
- `_pick_col()` : Sélectionne une colonne parmi des candidats
- `_to_number()` : Convertit une série en nombres
- `_is_all_upper()` : Vérifie si une chaîne est en MAJUSCULES
- `summary()` : Résumé des données
- `get_latest_period()` : Retourne la dernière période disponible

**Utilisation** : ✅ **UTILISÉ** dans :
- `logic/kpi_engine.py` : Chargement des données pour calculs KPI
- `logic/analytics.py` : Chargement des données pour analyses
- `ui/data_provider.py` : Chargement des données

**Action** : **CONSERVER** (module utilitaire actif)

---

### 9. `reports.py` ✅
**Rôle** : Génération de rapports Excel et PDF  
**Fonctions principales** :
- `df_resume_mois()` : DataFrame résumé du mois
- `df_detail_employe()` : DataFrame détail par employé
- `df_rep_code_paie()` : DataFrame répartition par code de paie
- `df_rep_poste_budgetaire()` : DataFrame répartition par poste budgétaire
- `df_evolution_12p()` : DataFrame évolution sur 12 périodes
- `df_anomalies()` : DataFrame des anomalies
- `export_excel_*()` : Export Excel pour différents rapports
- `export_pdf_*()` : Export PDF pour différents rapports

**Utilisation** : ✅ **UTILISÉ** dans :
- `ui/menus/reports_menu.py` : Menu de génération de rapports

**Action** : **CONSERVER** (module actif pour exports)

---

## Résumé des Actions Recommandées

### ✅ À CONSERVER (Modules Actifs)
1. `__init__.py` - Nécessaire pour package Python
2. `audit.py` - Utilisé pour audits et détection d'anomalies
3. `formatting.py` - Utilisé pour formatage (nombres, dates)
4. `insights.py` - Utilisé pour génération d'insights
5. `metrics.py` - Utilisé pour chargement de données
6. `reports.py` - Utilisé pour génération de rapports Excel/PDF

### ⚠️ À ARCHIVER (Modules Obsolètes/Non Utilisés)
1. `analytics.py` - Remplacé par `providers/postgres_provider.py` et `api/routes/kpi.py`
2. `db_optimizer.py` - Non utilisé (optimisation gérée par migrations SQL)
3. `kpi_engine.py` - Partiellement utilisé, remplacé par providers PostgreSQL

---

## Recommandations

### Option 1 : Nettoyage Minimal (Recommandé)
- **Conserver** tous les fichiers (même obsolètes) pour référence future
- **Documenter** les modules obsolètes dans les commentaires

### Option 2 : Nettoyage Complet
- **Archiver** `analytics.py`, `db_optimizer.py`, `kpi_engine.py` dans `archive/logic/`
- **Conserver** uniquement les modules actifs

### Option 3 : Refactoring
- **Intégrer** les fonctionnalités utiles des modules obsolètes dans les providers actuels
- **Supprimer** les modules obsolètes après migration

---

## Notes Importantes

1. **Dépendances** : Les modules `logic/` dépendent de `services/data_repo.py` pour l'accès PostgreSQL
2. **Compatibilité** : Certains modules utilisent encore l'ancien format de données (DataFrame pandas) au lieu de requêtes SQL directes
3. **Migration** : L'application actuelle (Tabler UI) utilise principalement `providers/postgres_provider.py` et `api/routes/` pour les KPIs, mais certains modules `logic/` sont encore utilisés pour les audits et rapports

---

**Date d'analyse** : 2025-01-XX  
**Version application** : PayrollAnalyzer_Etape0

