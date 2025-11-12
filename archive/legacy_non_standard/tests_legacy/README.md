Legacy code and removed providers
===============================

Ce dossier contient des copies historiques de providers et d'implémentations
déplacées hors du chemin d'exécution principal. Les fichiers ici sont conservés
uniquement pour référence ou restauration manuelle.

Raisons du retrait
- La stratégie du projet a évolué vers une connexion PostgreSQL stricte
  (psycopg, DSN avec mot de passe). Les providers hybrides/fallback/offline
  pouvaient entraîner des démarrages sans authentification ou avec des
  comportements inattendus. Ils ont donc été retirés du code actif.

Restaurer un provider (si nécessaire)
1. Copier le fichier dans `app/providers/`
2. Vérifier les impacts au démarrage (tests A/B/C) et préférer un
   environnement de développement isolé.

Fichiers archivés:
- providers/hybrid_provider.py
- providers/hybrid_provider.py.bak
