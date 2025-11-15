# Vues d'Agrégation par Mois et par Année

## Principe

**Règle fondamentale**: Une "période de paie" est **toujours une date exacte** (YYYY-MM-DD), pas un mois ni une année.

Cependant, pour des besoins d'analyse et de reporting, vous pouvez avoir besoin d'agrégations par mois ou par année.

## Vues Disponibles

### 1. Vue par Date Exacte (Période de Paie)

**`payroll.v_kpi_periode`** - Vue principale par date exacte
```sql
SELECT * FROM payroll.v_kpi_periode 
WHERE date_paie = '2025-08-28';
```

**Colonnes**:
- `date_paie` (YYYY-MM-DD) - Date exacte de paie

### 2. Vue d'Agrégation Mensuelle

**`payroll.v_kpi_agregation_mensuelle`** - Agrégation par mois
```sql
SELECT * FROM payroll.v_kpi_agregation_mensuelle 
WHERE mois = '2025-08';
```

**Colonnes**:
- `mois` (YYYY-MM) - Mois d'agrégation
- `annee` (YYYY) - Année
- `nb_dates_paie` - Nombre de dates de paie distinctes dans le mois
- Tous les KPI agrégés (gains_brut, deductions_net, etc.)

### 3. Vue d'Agrégation Annuelle

**`payroll.v_kpi_agregation_annuelle`** - Agrégation par année
```sql
SELECT * FROM payroll.v_kpi_agregation_annuelle 
WHERE annee = '2025';
```

**Colonnes**:
- `annee` (YYYY) - Année d'agrégation
- `nb_dates_paie` - Nombre de dates de paie distinctes dans l'année
- `nb_mois` - Nombre de mois distincts dans l'année
- Tous les KPI agrégés

### 4. Vue d'Agrégation Mensuelle par Catégorie

**`payroll.v_kpi_agregation_mensuelle_par_categorie`** - Mois + Catégorie d'emploi
```sql
SELECT * FROM payroll.v_kpi_agregation_mensuelle_par_categorie 
WHERE mois = '2025-08' AND categorie_emploi = 'Permanent';
```

## Exemples d'Utilisation

### Obtenir les KPI pour une date exacte
```sql
SELECT * FROM payroll.v_kpi_periode 
WHERE date_paie = '2025-08-28';
```

### Obtenir les KPI agrégés pour un mois
```sql
SELECT * FROM payroll.v_kpi_agregation_mensuelle 
WHERE mois = '2025-08';
```

### Obtenir les KPI agrégés pour une année
```sql
SELECT * FROM payroll.v_kpi_agregation_annuelle 
WHERE annee = '2025';
```

### Évolution mensuelle (12 derniers mois)
```sql
SELECT mois, gains_brut, nb_employes, nb_dates_paie
FROM payroll.v_kpi_agregation_mensuelle
WHERE mois >= TO_CHAR(CURRENT_DATE - INTERVAL '12 months', 'YYYY-MM')
ORDER BY mois;
```

### Comparaison année sur année
```sql
SELECT annee, gains_brut, nb_employes, nb_mois
FROM payroll.v_kpi_agregation_annuelle
WHERE annee IN ('2024', '2025')
ORDER BY annee;
```

## Différence Importante

- **`date_paie`** = Date exacte de paie (YYYY-MM-DD) - Utilisé pour les opérations métier
- **`mois`** = Mois d'agrégation (YYYY-MM) - Utilisé pour analyses/rapports
- **`annee`** = Année d'agrégation (YYYY) - Utilisé pour analyses/rapports

Les vues d'agrégation (`v_kpi_agregation_*`) sont **uniquement pour l'analyse**, pas pour les opérations métier qui nécessitent une date exacte.

