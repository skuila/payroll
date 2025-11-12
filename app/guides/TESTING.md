## TESTING - Standardisation des méthodes de test

But: séparer clairement les tests unitaires, d'intégration et end-to-end (GUI) afin d'éviter le mélange et améliorer la reproductibilité.

Structure recommandée:

- `tests/unit/` : tests rapides, sans dépendance à la base de données ni à l'UI (pytest)
- `tests/integration/` : tests nécessitant DB ou fichiers (marqués `integration`)
- `tests/e2e/` : tests UI (pytest-qt, besoin d'un affichage graphique ou CI configuré)

Exécuter les tests locaux rapides:

Powershell (depuis `app`):
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Pour exécuter seulement les tests unitaires:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q
```

Créer un test d'intégration:
 - placer le test dans `tests/integration/`
 - marquer avec `@pytest.mark.integration`

Guide rapide pour écrire des tests:
- Tests unitaires -> pas de PyQt, pas de DB.
- Tests d'intégration -> configurer variables d'environnement dans `tests/conftest.py` ou utiliser fixtures.
- Tests e2e (UI) -> utiliser `pytest-qt` et exécuter sur machine avec X/GUI ou runner CI qui supporte GUI.

Si vous voulez, je peux:
- ajouter `conftest.py` avec fixtures DB mock,
- ajouter un job GitHub Actions d'exemple pour lancer `pytest`.
