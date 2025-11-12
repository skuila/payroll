# PayrollAnalyzer

Application de gestion et d'analyse de la paie.

---

## 🚀 Démarrage Rapide

### Lancer l'application

```batch
cd C:\Users\SZERTYUIOPMLMM\Desktop\APP\app
LANCER_APP.bat
```

**C'est tout !** ✅

---

## 📚 Documentation Complète

Toute la documentation est centralisée dans le dossier **`guides/`**

### Guides Essentiels

- **[guides/INDEX.md](guides/INDEX.md)** - Index complet de tous les guides
- **[guides/GUIDE_CONNEXION.md](guides/GUIDE_CONNEXION.md)** - Guide de connexion et lancement
- **[guides/CONNEXION_STANDARDISEE.md](guides/CONNEXION_STANDARDISEE.md)** - Architecture standardisée
- **[guides/SCHEMA_APPLICATION.md](guides/SCHEMA_APPLICATION.md)** - Architecture de la base de données

---

## 🔧 Configuration

Le fichier `.env` contient toute la configuration :

```env
PAYROLL_DSN=postgresql://payroll_unified:password@127.0.0.1:5432/payroll_db
PAYROLL_DB_PASSWORD=password
APP_ENV=development
```

Voir [guides/GUIDE_CONNEXION.md](guides/GUIDE_CONNEXION.md) pour plus de détails.

---

## 🏗️ Architecture

```
app/
├── LANCER_APP.bat          # Lanceur principal ⭐
├── guides/                 # Documentation complète 📚
│   ├── INDEX.md           # Index des guides
│   ├── GUIDE_CONNEXION.md
│   └── ...
├── config/                 # Configuration
│   ├── connection_standard.py  # Module de connexion unifié
│   └── settings.py
├── services/              # Services métier
├── providers/             # Providers de données
├── ui/                    # Interface utilisateur
└── payroll_app_qt_Version4.py  # Application principale
```

---

## 🛠️ Scripts utiles

Les utilitaires compatibles avec la connexion standard sont disponibles dans `app/scripts/standardized/` :

- `check_connection.py` → test rapide de la base (`python app/scripts/standardized/check_connection.py`)
- `db_overview.py` → export JSON des tables principales (`python app/scripts/standardized/db_overview.py out/db.json`)
- `export_employees.py` → export CSV des employés (`python app/scripts/standardized/export_employees.py out/employees.csv --limit 100`)

Les anciens scripts non conformes sont conservés dans `archive/legacy_non_standard/` à titre documentaire uniquement.

---

## 🧪 Tests

```batch
# Test de connexion
python config/connection_standard.py

# Lancer l'application
LANCER_APP.bat
```

Voir [guides/TESTING.md](guides/TESTING.md) pour plus de tests.

---

## 📞 Support

1. Consulter [guides/INDEX.md](guides/INDEX.md)
2. Lire le guide approprié
3. Vérifier la section "Résolution de problèmes"

---

**Version :** 1.0  
**Date :** 2025-11-11  
**Statut :** ✅ Production

