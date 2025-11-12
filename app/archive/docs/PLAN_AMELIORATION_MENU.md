# 📋 Plan d'Amélioration du Menu et Connexions

## État Actuel du Menu (index.html)

### Pages Principales Connectées ✅
- ✅ **Accueil** (`index.html`) - Dashboard principal
- ✅ **Employés** (`employees.html`) - Liste des employés
- ✅ **Base de données** (`database.html`) - Gestion DB
- ✅ **Assistant IA** (`assistant.html`) - Chat IA
- ✅ **Importer des données** (`import.html`) - Import Excel

### Pages Manquantes ou Non Connectées ⚠️
- ⚠️ **Tableau de bord KPI** (`kpi-dashboard.html`) - **À créer**
- ⚠️ **Analyses** (`analytics.html`) - Existe mais connexion incomplète
- ⚠️ **Périodes** - Pas dans le menu (existe `periods.html`)
- ⚠️ **Rapports** - Pas dans le menu
- ⚠️ **Visualisation de données** (`data-viewer.html`) - Pas dans le menu

### Menu "Interface" (Exemples Tabler) 🗑️
Ce menu contient des exemples Tabler non utilisés. À **réorganiser** ou **retirer**.

---

## Plan d'Action

### Phase 1 : Compléter le Menu Principal (Priorité Haute)

#### 1. Ajouter les pages manquantes au menu

**Menu suggéré :**
```
📊 Accueil (index.html) ✅
📈 Tableau de bord KPI (kpi-dashboard.html) ⚠️ À créer
📉 Analyses (analytics.html) ⚠️ À connecter
👥 Employés (employees.html) ✅
📅 Périodes (periods.html) ⚠️ À ajouter
💾 Base de données (database.html) ✅
📥 Importer des données (import.html) ✅
📊 Visualisation (data-viewer.html) ⚠️ À ajouter
📄 Rapports (period-report.html) ⚠️ À ajouter
🤖 Assistant IA (assistant.html) ✅
```

#### 2. Créer `kpi-dashboard.html`
Page dédiée aux KPIs avec graphiques avancés.

#### 3. Connecter `analytics.html` à l'API
Utiliser le nouveau `api-client.js`.

---

### Phase 2 : Améliorer la Navigation (Priorité Moyenne)

#### 1. Ajouter un menu "Rapports"
```
📄 Rapports
  ├── Rapport par période
  ├── Rapport employé
  └── Exports
```

#### 2. Ajouter un menu "Paramètres"
```
⚙️ Paramètres
  ├── Configuration base de données
  ├── Préférences utilisateur
  └── À propos
```

#### 3. Ajouter breadcrumbs (fil d'Ariane)
Pour faciliter la navigation.

---

### Phase 3 : Optimisations UX (Priorité Basse)

#### 1. Indicateur de page active
Le menu doit mettre en évidence la page courante.

#### 2. Menu responsive
S'assurer que le menu fonctionne sur mobile.

#### 3. Raccourcis clavier
Ajouter des raccourcis pour naviguer rapidement.

---

## Actions Immédiates

### 1. Créer `api-client.js` ✅ FAIT
Client API unifié créé dans `web/tabler/js/api-client.js`

### 2. Modifier `index.html` pour inclure `api-client.js`
Ajouter dans le `<head>` :
```html
<script src="./js/api-client.js"></script>
```

### 3. Ajouter les pages manquantes au menu
Modifier la section `<ul class="navbar-nav">` dans `index.html`

### 4. Créer `kpi-dashboard.html`
Page dédiée avec graphiques ApexCharts.

---

## Fichiers à Modifier

### Fichiers à Modifier
- ✅ `web/tabler/js/api-client.js` - **CRÉÉ**
- ⚠️ `web/tabler/index.html` - Ajouter script + menu
- ⚠️ `web/tabler/kpi-dashboard.html` - **À CRÉER**
- ⚠️ `web/tabler/analytics.html` - Connecter à l'API
- ⚠️ Toutes les autres pages - Utiliser `api-client.js`

### Fichiers à Créer
- ⚠️ `web/tabler/kpi-dashboard.html`
- ⚠️ `web/tabler/js/ui-helpers.js` - Helpers UI (loading, errors, etc.)

---

## Prochaines Étapes

1. **Inclure `api-client.js` dans toutes les pages**
2. **Modifier le menu dans `index.html`** pour ajouter pages manquantes
3. **Créer `kpi-dashboard.html`**
4. **Connecter toutes les pages à l'API** via `api-client.js`
5. **Tester toutes les connexions**

---

## Commandes pour Tester

```bash
# Vérifier que l'API FastAPI est démarrée
curl http://localhost:8001/health

# Tester un endpoint KPI
curl http://localhost:8001/kpi/2025-08

# Vérifier les périodes
curl http://localhost:8001/periods
```

---

**Priorité** : Commencer par modifier le menu dans `index.html` et ajouter les pages manquantes.







