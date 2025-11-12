# 🔧 Solution Problème Pare-feu/Antivirus

## Problème
Le pare-feu ou l'antivirus bloque les connexions depuis `file://` vers `localhost:8088` dans l'iframe.

## ✅ Solution : Serveur HTTP Local

### Option 1 : Utiliser le serveur HTTP local (Recommandé)

**Étape 1** : Démarrer le serveur
```powershell
python servir_html_local.py
```

Le serveur démarre sur `http://localhost:3000` et ouvre automatiquement `analytics.html`.

**Étape 2** : Dans votre application PyQt, modifier `TablerViewer` pour utiliser le serveur :

```python
# Dans ui/tabler_viewer.py, méthode load_page
if filename == "analytics.html":
    # Utiliser le serveur HTTP local au lieu de file://
    url = QUrl("http://localhost:3000/analytics.html")
else:
    url = QUrl.fromLocalFile(str(html_path))
```

**Étape 3** : Ou simplement ouvrir dans le navigateur :
```
http://localhost:3000/analytics.html
```

### Option 2 : Configurer le pare-feu Windows (Alternative)

1. Ouvrir le Pare-feu Windows Defender
2. Paramètres avancés
3. Règles de trafic entrant → Nouvelle règle
4. Autoriser les connexions TCP sur le port 8088 depuis localhost
5. Répéter pour les connexions sortantes

### Option 3 : Autoriser localhost dans l'antivirus

1. Ouvrir les paramètres de votre antivirus
2. Chercher "Exceptions" ou "Liste blanche"
3. Ajouter `localhost` et `127.0.0.1`

## Solution Rapide (Recommandée)

**Dans un nouveau terminal PowerShell** :
```powershell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0
python servir_html_local.py
```

Puis dans votre application, modifier temporairement pour utiliser :
```
http://localhost:3000/analytics.html
```

Ou simplement ouvrir dans le navigateur :
```
http://localhost:3000/analytics.html
```

## Pourquoi ça fonctionne ?

- ✅ `http://localhost:3000` est autorisé par le pare-feu (HTTP standard)
- ✅ Évite les restrictions `file://` vers `localhost`
- ✅ Pas besoin de modifier les paramètres de sécurité





