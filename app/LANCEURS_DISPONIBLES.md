# Lanceurs d'Application PayrollAnalyzer

## 🚀 Lanceur Principal (Recommandé)

### `LANCER_APP.bat`
**Lanceur standard pour Windows**
- Lance directement l'application principale
- Configuration automatique du PYTHONPATH
- Gestion des erreurs avec messages clairs

**Utilisation:**
```batch
cd app
LANCER_APP.bat
```

---

## 🐍 Lanceurs Python (Avancés)

### `launch_payroll.py`
**Lanceur Python unifié avec vérifications**
- Vérifie la connexion PostgreSQL avant lancement
- Configure automatiquement les variables d'environnement
- Gestion d'erreurs complète

**Utilisation:**
```bash
cd app
python launch_payroll.py
```

### `launch_debug.py`
**Lanceur avec logs détaillés pour diagnostic**
- Affiche toutes les étapes de configuration
- Test de connexion DB avec détails
- Utile pour résoudre les problèmes de connexion

**Utilisation:**
```bash
cd app
python launch_debug.py
```

---

## 📝 Notes

- **Lanceur recommandé:** `LANCER_APP.bat` (le plus simple)
- **Pour debug:** `launch_debug.py` (logs détaillés)
- **Pour intégration:** `launch_payroll.py` (vérifications complètes)

---

**Dernière mise à jour:** 2025-11-13

