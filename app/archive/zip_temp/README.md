# PayrollAnalyzer - Application Complète

## 📦 Contenu du ZIP

Ce ZIP contient l'application PayrollAnalyzer complète avec:
- Code source Python (backend)
- Interface Tabler (frontend)
- Migrations SQL
- Dumps de base de données (structure + données)
- Documentation technique complète

## 🚀 Installation rapide

### Prérequis

- Python 3.10+
- PostgreSQL 17
- PyQt6 (pour l'interface desktop)

### Installation

1. **Extraire le ZIP**
   ```bash
   unzip PayrollAnalyzer_Complete_*.zip
   cd PayrollAnalyzer_Complete_*/
   ```

2. **Installer les dépendances Python**
   ```bash
   pip install -r requirements.txt
   # ou
   pip install PyQt6 psycopg[binary] fastapi uvicorn pandas python-dotenv
   ```

3. **Configurer PostgreSQL**
   - Créer la base: `CREATE DATABASE payroll_db;`
   - Restaurer la structure: `psql -d payroll_db -f database/schema_dump.sql`
   - Restaurer les données: `psql -d payroll_db -f database/data_dump.sql`
   - OU appliquer les migrations dans l'ordre:
     ```bash
     psql -d payroll_db -f migration/01_ddl_referentiel.sql
     psql -d payroll_db -f migration/014_unicite_matricule_et_vues_kpi.sql
     # ... etc
     ```

4. **Configurer les variables d'environnement**
   - Créer `.env` avec:
     ```
     PAYROLL_DSN=postgresql://payroll_app:PayrollApp2025!@localhost:5432/payroll_db
     ```

5. **Démarrer l'application**
   ```bash
   python payroll_app_qt_Version4.py
   # ou
   DEMARRER.bat
   ```

## 📚 Documentation

- **CONTEXT.md**: Documentation technique complète (architecture, règles de calcul, etc.)
- **migration/README_EXECUTION.md**: Guide d'exécution des migrations

## 🔐 Sécurité

⚠️ **ATTENTION**: Ce ZIP contient les mots de passe réels de la base de données.

Avant de partager ou utiliser en production:
1. Changer les mots de passe PostgreSQL
2. Mettre à jour les variables d'environnement
3. Revoir les permissions des rôles PostgreSQL

## 📞 Support

Pour toute question, consulter:
- `CONTEXT.md` pour la documentation technique
- Les logs dans `logs/` (si disponibles)
- Les commentaires dans le code source

---

**Version**: 2.0.1
**Date**: 2025-11-05
