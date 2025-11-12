## Instructions rapides pour agents (français)

But: aider un contributeur humain à vérifier, analyser et proposer de petits correctifs sur ce dépôt "PayrollAnalyzer".

1) Contexte global
 - Application desktop PyQt6 (interface graphique) — lancement standard: `python launch_payroll.py` (voir `app/README.md`).
 - Connexion stricte PostgreSQL au démarrage : la variable `PAYROLL_DSN` (ou `PGPASSWORD` + host/user) est requise. Si la DB n'est pas accessible, l'application quitte (exit=1).
 - Ce dépôt n'offre pas d'API web : privilégiez l'inspection du code et des scripts locaux (`inspect_view.py`, `connect_check.py`).

2) Actions attendues d'un agent IA
 - Lire d'abord `app/README.md` puis `app/config/mapping_entetes.yml` (fichier de mapping ETL) pour comprendre les règles métier.
 - Pour toute modification fonctionnelle, proposer une PR petite et ciblée avec un test si possible (`tests/` — `pytest` est utilisé, voir `app/pytest.ini`).
 - Ne jamais modifier la configuration de connexion DB dans le repo; proposer des instructions d'exécution (ex: `PAYROLL_DSN`) dans la PR si nécessaire.

3) Commandes utiles (exemples)
 - Lancer les tests unitaires: depuis `app/`: `pytest -q` (pytest >=7.0 dans `requirements.txt`).
 - Vérifier la connexion DB rapidement: `python inspect_view.py` (script fourni pour tests d'accès).
 - Lancer l'application GUI (dev only): `python launch_payroll.py --dsn "postgresql://user:pwd@host:5432/db"` ou définir `PAYROLL_DSN`.

4) Fichiers et conventions clés (à lire en priorité)
 - `app/README.md` : démarrage, DSN et comportement au démarrage.
 - `app/config/mapping_entetes.yml` : règles ETL—variantes de colonnes, normalisations et validations (important pour tout changement d'import CSV/Excel).
 - `requirements.txt` : dépendances (PyQt6, SQLAlchemy, psycopg, pandas, pytest).
 - `app/pytest.ini` : configuration des tests (tests dans `tests/`, fichiers `test_*.py`).
 - Scripts de diagnostic : `inspect_view.py`, `connect_check.py`, `export_db_info.py`.
 - Bases de données/migrations: `alembic.ini` et SQLs sous `app/` (rechercher `alembic` si modification de schéma).

5) Patterns et règles spécifiques au projet
 - Import/ETL : les mappings sont déclaratifs dans `app/config/mapping_entetes.yml` (ne pas coder en dur les variantes de colonnes ailleurs).
 - Normalisation des montants : convertir en cents (multiply_by_100) — attention aux parenthèses -> négatif.
 - Validation stricte : `date_paie` et `matricule` sont obligatoires; l'application rejette/arrête si règles critiques non respectées.
 - Pas d'endpoints REST ni d'appel réseau côté UI — le code est desktop-only.

6) PR et style d'intervention
 - Pour corrections mineures (typo, logs, messages d'erreur) : créer une PR branch `fix/<sujet>` avec description courte et tests si possible.
 - Pour changements ETL ou validation : documenter l'impact sur `mapping_entetes.yml` et ajouter un exemple d'entrée/sortie dans la PR description.
 - Si une modification nécessite une DB réelle pour validation, fournir instructions claires pour créer une DB de test ou un dump anonymisé.

7) Limitations et sécurité
 - Ne pas commiter de secrets (DSN, mots de passe, tokens). Proposer l'usage d'un `.env` ou variables d'environnement.
 - Ne pas tenter d'exécuter le GUI dans des environnements CI sans display (utiliser `pytest-qt` pour tests UI quand nécessaire).

Si une section est incomplète ou si vous voulez que j'ajoute des commandes exactes pour CI / création d'un repo GitHub privé, dites-le et j'ajusterai le fichier.
