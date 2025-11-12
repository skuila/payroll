# Guide de Connexion Standardisé - PayrollAnalyzer

## 📋 Résumé

**Méthode unique et standardisée** pour lancer l'application sans problème de connexion.

---

## 🚀 Lancement de l'Application

### Méthode Recommandée (Windows)

```batch
cd C:\Users\SZERTYUIOPMLMM\Desktop\APP\app
LANCER_APP.bat
```

**C'est tout !** Le fichier BAT configure automatiquement :
- ✅ PYTHONPATH
- ✅ Variables d'environnement (.env)
- ✅ Connexion PostgreSQL
- ✅ Interface PyQt6

---

## 🔧 Configuration (Fichier .env)

Le fichier `app/.env` contient TOUTE la configuration :

```env
# Configuration PostgreSQL (OBLIGATOIRE)
PAYROLL_DSN=postgresql://payroll_unified:aq456*456@127.0.0.1:5432/payroll_db?application_name=PayrollApp&sslmode=disable
PGPASSWORD=aq456*456
PAYROLL_DB_PASSWORD=aq456*456

# Environnement
APP_ENV=development
```

### Variables Supportées

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `PAYROLL_DSN` | DSN complet PostgreSQL | ✅ OUI |
| `PAYROLL_DB_PASSWORD` | Mot de passe DB | ✅ OUI |
| `PGPASSWORD` | Mot de passe (fallback) | Recommandé |
| `PAYROLL_DB_HOST` | Hôte (défaut: localhost) | Non |
| `PAYROLL_DB_PORT` | Port (défaut: 5432) | Non |
| `PAYROLL_DB_NAME` | Nom DB (défaut: payroll_db) | Non |
| `PAYROLL_DB_USER` | Utilisateur (défaut: payroll_unified) | Non |

---

## 🔍 Diagnostic de Connexion

### Test Rapide

```batch
cd C:\Users\SZERTYUIOPMLMM\Desktop\APP\app
python config/connection_standard.py
```

**Sortie attendue :**
```
✅ DSN: postgresql://payroll_unified:****@...
✅ Connecté: payroll_unified@payroll_db
✅ Pool initialisé
✅ TOUS LES TESTS PASSENT
```

### Test Connexion Simple

```batch
python connect_check.py
```

---

## 📚 Utilisation dans le Code

### Import Standard

```python
# TOUJOURS utiliser ce module pour les connexions
from config.connection_standard import get_dsn, get_connection_pool, test_connection

# Obtenir le DSN
dsn = get_dsn()

# Obtenir le pool de connexions (singleton)
pool = get_connection_pool()

# Exécuter une requête
result = pool.run_query("SELECT * FROM core.employees LIMIT 10")

# Tester la connexion
status = test_connection()
if status['success']:
    print(f"Connecté: {status['user']}@{status['database']}")
```

### ❌ À NE PAS FAIRE

```python
# ❌ NE PAS construire le DSN manuellement
dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

# ❌ NE PAS créer plusieurs pools
pool1 = DataRepository(dsn)
pool2 = DataRepository(dsn)  # Mauvais !

# ❌ NE PAS lire os.getenv() directement
password = os.getenv('PAYROLL_DB_PASSWORD')  # Utiliser get_dsn() à la place
```

### ✅ À FAIRE

```python
# ✅ Utiliser le module standard
from config.connection_standard import get_connection_pool

pool = get_connection_pool()
result = pool.run_query("SELECT ...")
```

---

## 🛠️ Résolution de Problèmes

### Problème: "No password supplied"

**Solution:**
1. Vérifier que `app/.env` existe
2. Vérifier que `PAYROLL_DSN` contient le mot de passe
3. OU définir `PAYROLL_DB_PASSWORD`

```env
PAYROLL_DSN=postgresql://user:MOT_DE_PASSE@host:5432/db
```

### Problème: "Module 'app.services' not found"

**Solution:**
Toujours lancer depuis `LANCER_APP.bat` qui configure `PYTHONPATH` automatiquement.

OU définir manuellement :
```batch
set PYTHONPATH=C:\Users\SZERTYUIOPMLMM\Desktop\APP
python payroll_app_qt_Version4.py
```

### Problème: "Connection timeout"

**Solution:**
1. Vérifier que PostgreSQL est démarré :
   ```powershell
   Get-Service postgresql*
   ```
2. Tester la connexion :
   ```batch
   python config/connection_standard.py
   ```

### Problème: Application se ferme immédiatement

**Solution:**
Utiliser `LANCER_APP.bat` qui garde la console ouverte et affiche les erreurs.

---

## 📝 Checklist de Démarrage

Avant de lancer l'application, vérifier :

- [ ] PostgreSQL est démarré (`Get-Service postgresql*`)
- [ ] Le fichier `app/.env` existe
- [ ] `PAYROLL_DSN` est défini dans `.env`
- [ ] Le mot de passe est présent dans le DSN
- [ ] Vous êtes dans le répertoire `app/`
- [ ] Vous utilisez `LANCER_APP.bat`

---

## 🎯 Commandes Rapides

```batch
# Lancer l'application
cd C:\Users\SZERTYUIOPMLMM\Desktop\APP\app
LANCER_APP.bat

# Tester la connexion
python config/connection_standard.py

# Vérifier PostgreSQL
Get-Service postgresql*

# Voir les variables d'environnement
Get-Content .env
```

---

## 📞 Support

En cas de problème persistant :

1. Exécuter le diagnostic complet :
   ```batch
   python config/connection_standard.py
   ```

2. Vérifier les logs dans la console

3. Consulter ce guide : `app/guides/GUIDE_CONNEXION.md`

---

**Version:** 1.0  
**Date:** 2025-11-11  
**Auteur:** Système standardisé

