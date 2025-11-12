# PayrollAnalyzer (mode desktop seulement)

- Lancement: `python launch_payroll.py`
- Données: accès direct PostgreSQL (pas d’API FastAPI, pas de Chrome).
- Config DB: via variables d’environnement
  - `PAYROLL_DSN` (prioritaire), ou `PAYROLL_DB_HOST/PORT/NAME/USER/PASSWORD`.
- Dépendances clés: PyQt6, PyQt6-WebEngine, SQLAlchemy, psycopg[binary], psycopg_pool, python-dotenv, pandas.

## Connexion DB (stricte)

Cette application exige désormais une connexion PostgreSQL stricte au démarrage.

- Utiliser un DSN complet avec mot de passe: `PAYROLL_DSN` (prioritaire) ou passer `--dsn` à `launch_payroll.py`.
- Exemples `.env`:

```env
# Exemple DSN avec encodage du mot de passe (si caractères spéciaux)
PAYROLL_DSN=postgresql://payroll_unified:%2Fmy%40p%24ssw0rd%21@127.0.0.1:5432/payroll_db
# Ou définir PGPASSWORD pour éviter l'inclusion dans le DSN
PGPASSWORD=MyS3cretP@ss
```

Note: si votre mot de passe contient `@`, `:` ou autres caractères réservés, encodez-le en URL (percent-encoding) ou définissez `PGPASSWORD`.

Comportement au démarrage:
- Si aucun DSN/mot de passe valide n'est trouvé → l'application affiche une erreur FR claire et quitte (exit=1).
- Si la connexion PostgreSQL est établie, un seul message de succès est journalisé au format:

```
SUCCESS: Connexion PostgreSQL établie (app=<dsn_masked>, db=<db>, user=<user>)
```

Tester la connexion depuis l'interface:
- Dans l'application, menu Aide → `Tester la connexion DB…` lance un test éphémère et affiche PASS/FAIL.

Rational: suppression des modes fallback/hybride/offline pour éviter des démarrages sans authentification ou avec données partielles.

Note: Les anciens lanceurs (batch, helpers) ont été archivés dans `archive/disabled_launchers/`.
Utilisez `launch_payroll.py` comme méthode standard pour démarrer l'application et assurer la
vérification préalable de la connexion à la base de données.

Tests rapides (PowerShell):
- `python inspect_view.py` → teste la connexion et lit une vue.
- `python tmp_check_employees.py` → extrait un échantillon d’employés.

Toutes les références à FastAPI/uvicorn/requests et fetch('/…') ont été supprimées du code actif.



