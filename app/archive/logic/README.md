# Modules Logic Archivés

Ce dossier contient les modules du dossier `logic/` qui ont été archivés car ils ne sont plus utilisés dans l'application actuelle.

## Fichiers Archivés

### `analytics.py`
**Raison d'archivage** : Remplacé par `providers/postgres_provider.py` et `api/routes/kpi.py`  
**Fonctionnalités** : Calcul des KPIs, détection d'anomalies, comparaisons de périodes  
**Date d'archivage** : 2025-01-XX

### `db_optimizer.py`
**Raison d'archivage** : Non utilisé - L'optimisation est gérée directement par les migrations SQL et les providers  
**Fonctionnalités** : Vérification d'index PostgreSQL, gestion du cache KPI  
**Date d'archivage** : 2025-01-XX

### `kpi_engine.py`
**Raison d'archivage** : Partiellement utilisé mais remplacé par les providers PostgreSQL  
**Fonctionnalités** : Moteur de calcul des KPI avancés (financiers, RH, tendances, alertes)  
**Date d'archivage** : 2025-01-XX

## Modules Conservés dans `logic/`

Les modules suivants sont toujours actifs et utilisés :
- `audit.py` - Audit et détection d'anomalies
- `formatting.py` - Formatage nombres/dates
- `insights.py` - Génération d'insights textuels
- `metrics.py` - Chargement de données depuis PostgreSQL
- `reports.py` - Génération de rapports Excel/PDF

## Note

Ces fichiers sont conservés pour référence future. Si vous avez besoin de restaurer l'un de ces modules, déplacez-le simplement de `archive/logic/` vers `logic/`.




