<!-- a0e8aeea-9cb0-4a73-bc76-cf88643bf085 6526b183-7fcd-4504-bdb8-f3396bbf486d -->
# Integration Tabler Officiel Offline - PayrollAnalyzer

## Objectif

Télécharger et intégrer le pack Tabler OFFICIEL complet en local (offline) sans modifier l'UI PyQt6 existante. Aucun CDN, aucun QSS custom, uniquement les assets Tabler originaux.

## 1. Téléchargement du pack Tabler officiel

### Télécharger depuis GitHub

- URL: https://github.com/tabler/tabler/releases/latest
- Télécharger l'archive `tabler-[version].zip` de la dernière version stable
- Extraire l'archive temporairement

### Assets à récupérer

- `dist/css/` - Fichiers CSS minifiés (tabler.min.css, tabler-vendors.min.css)
- `dist/js/` - Fichiers JavaScript (tabler.min.js, tabler.esm.min.js)
- `dist/libs/` - Bibliothèques tierces (apexcharts, autoComplete, etc.)
- `dist/fonts/` - Polices Inter et autres (si présentes)
- `demo/` ou `examples/` - Pages d'exemples HTML (dashboard.html, login.html, etc.)

### Télécharger Tabler Icons

- URL: https://github.com/tabler/tabler-icons/releases/latest
- Télécharger l'archive complète des icônes SVG
- Extraire tous les fichiers SVG

## 2. Création de l'arborescence locale

### Structure `web/tabler/`

```
web/tabler/
├── dist/
│   ├── css/
│   │   ├── tabler.min.css
│   │   ├── tabler.min.css.map
│   │   ├── tabler-vendors.min.css
│   │   └── tabler-vendors.min.css.map
│   ├── js/
│   │   ├── tabler.min.js
│   │   ├── tabler.min.js.map
│   │   ├── tabler.esm.min.js
│   │   └── tabler.esm.min.js.map
│   ├── libs/
│   │   ├── apexcharts/
│   │   ├── autoComplete/
│   │   ├── fslightbox/
│   │   ├── jsvectormap/
│   │   ├── litepicker/
│   │   ├── nouislider/
│   │   ├── plyr/
│   │   ├── tinymce/
│   │   └── tom-select/
│   └── fonts/
│       └── (polices si présentes)
├── icons/
│   ├── arrow-down.svg
│   ├── arrow-up.svg
│   ├── chart-line.svg
│   ├── currency-dollar.svg
│   ├── users.svg
│   ├── calendar.svg
│   ├── trending-up.svg
│   ├── trending-down.svg
│   ├── alert-circle.svg
│   ├── settings.svg
│   ├── dashboard.svg
│   └── (tous les autres SVG Tabler Icons - ~4700 icônes)
├── examples/
│   ├── dashboard.html
│   ├── login.html
│   ├── cards.html
│   ├── charts.html
│   ├── tables.html
│   └── (toutes les autres pages d'exemple)
└── app_bridge.js (placeholder vide pour QWebChannel futur)
```

### Créer les répertoires

```bash
mkdir -p web/tabler/dist/css
mkdir -p web/tabler/dist/js
mkdir -p web/tabler/dist/libs
mkdir -p web/tabler/dist/fonts
mkdir -p web/tabler/icons
mkdir -p web/tabler/examples
```

### Copier les fichiers téléchargés

- Copier `dist/css/*` vers `web/tabler/dist/css/`
- Copier `dist/js/*` vers `web/tabler/dist/js/`
- Copier `dist/libs/*` vers `web/tabler/dist/libs/`
- Copier `dist/fonts/*` vers `web/tabler/dist/fonts/` (si présent)
- Copier tous les SVG vers `web/tabler/icons/`
- Copier toutes les pages d'exemple vers `web/tabler/examples/`

### Créer app_bridge.js

```javascript
// web/tabler/app_bridge.js
// Placeholder pour intégration future avec QWebChannel
// Permet la communication bidirectionnelle Python ↔ JavaScript
console.log('Tabler App Bridge ready (placeholder)');
```

## 3. Correction des liens CDN vers chemins locaux

### Fichiers à modifier

Tous les fichiers HTML dans `web/tabler/examples/*.html`

### Patterns à remplacer

#### CSS CDN → Local

```html
<!-- AVANT (CDN) -->
<link href="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler.min.css" rel="stylesheet"/>
<link href="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler-vendors.min.css" rel="stylesheet"/>

<!-- APRÈS (LOCAL) -->
<link href="../dist/css/tabler.min.css" rel="stylesheet"/>
<link href="../dist/css/tabler-vendors.min.css" rel="stylesheet"/>
```

#### JavaScript CDN → Local

```html
<!-- AVANT (CDN) -->
<script src="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/js/tabler.min.js"></script>

<!-- APRÈS (LOCAL) -->
<script src="../dist/js/tabler.min.js"></script>
```

#### Libs CDN → Local

```html
<!-- AVANT (CDN) -->
<script src="https://cdn.jsdelivr.net/npm/apexcharts@latest"></script>

<!-- APRÈS (LOCAL) -->
<script src="../dist/libs/apexcharts/dist/apexcharts.min.js"></script>
```

#### Icons CDN → Local

```html
<!-- AVANT (CDN) -->
<svg class="icon">
  <use href="https://cdn.jsdelivr.net/npm/@tabler/icons@latest/sprite.svg#icon-name"/>
</svg>

<!-- APRÈS (LOCAL) -->
<svg class="icon">
  <use href="../icons/icon-name.svg#icon-name"/>
</svg>
```

### Script de remplacement automatique

Créer un script Python `tools/fix_tabler_links.py`:

```python
import os
import re
from pathlib import Path

EXAMPLES_DIR = Path("web/tabler/examples")

def fix_cdn_links(html_content):
    # CSS
    html_content = re.sub(
        r'https://cdn\.jsdelivr\.net/npm/@tabler/core@[^/]+/dist/css/',
        '../dist/css/',
        html_content
    )
    
    # JS
    html_content = re.sub(
        r'https://cdn\.jsdelivr\.net/npm/@tabler/core@[^/]+/dist/js/',
        '../dist/js/',
        html_content
    )
    
    # Libs (patterns multiples)
    html_content = re.sub(
        r'https://cdn\.jsdelivr\.net/npm/apexcharts@[^"\']+',
        '../dist/libs/apexcharts/dist/apexcharts.min.js',
        html_content
    )
    
    # Icons sprite
    html_content = re.sub(
        r'https://cdn\.jsdelivr\.net/npm/@tabler/icons@[^/]+/sprite\.svg',
        '../icons/',
        html_content
    )
    
    return html_content

# Parcourir tous les fichiers HTML
for html_file in EXAMPLES_DIR.glob("*.html"):
    content = html_file.read_text(encoding='utf-8')
    fixed_content = fix_cdn_links(content)
    html_file.write_text(fixed_content, encoding='utf-8')
    print(f"Fixed: {html_file.name}")
```

Exécuter: `python tools/fix_tabler_links.py`

## 4. Smoke Test optionnel (QWebEngineView)

### Créer `ui/tabler_viewer.py`

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QAction
import os

class TablerViewer(QWidget):
    """Viewer pour afficher les exemples Tabler en local (offline)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tabler UI Demo (Offline)")
        self.resize(1400, 900)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar pour navigation entre exemples
        toolbar = QToolBar()
        layout.addWidget(toolbar)
        
        # Actions pour différentes pages
        self.add_page_action(toolbar, "Dashboard", "dashboard.html")
        self.add_page_action(toolbar, "Cards", "cards.html")
        self.add_page_action(toolbar, "Charts", "charts.html")
        self.add_page_action(toolbar, "Tables", "tables.html")
        toolbar.addSeparator()
        
        reload_action = QAction("Recharger", self)
        reload_action.triggered.connect(self.reload_page)
        toolbar.addAction(reload_action)
        
        # WebEngineView
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Charger la page dashboard par défaut
        self.load_page("dashboard.html")
    
    def add_page_action(self, toolbar, label, filename):
        action = QAction(label, self)
        action.triggered.connect(lambda: self.load_page(filename))
        toolbar.addAction(action)
    
    def load_page(self, filename):
        base_path = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_path, "..", "web", "tabler", "examples", filename)
        html_path = os.path.abspath(html_path)
        
        if os.path.exists(html_path):
            url = QUrl.fromLocalFile(html_path)
            self.web_view.setUrl(url)
            print(f"Loading: {html_path}")
        else:
            print(f"File not found: {html_path}")
    
    def reload_page(self):
        self.web_view.reload()
```

### Ajouter menu dans `payroll_app_qt_Version4.py`

```python
# Dans la méthode __init__ de MainWindow, après création des menus existants

# Menu Développement (temporaire)
dev_menu = self.menuBar().addMenu("Développement")

# Action pour ouvrir le viewer Tabler
tabler_demo_action = QAction("UI Tabler (Demo Offline)", self)
tabler_demo_action.setStatusTip("Ouvrir les exemples Tabler en mode démo")
tabler_demo_action.triggered.connect(self.open_tabler_demo)
dev_menu.addAction(tabler_demo_action)

# Méthode pour ouvrir le viewer
def open_tabler_demo(self):
    from ui.tabler_viewer import TablerViewer
    self.tabler_viewer = TablerViewer()
    self.tabler_viewer.show()
```

## 5. Documentation

### Créer `MIGRATION_TABLER_GUIDE.md`

```markdown
# Guide Migration Tabler Officiel Offline

## Arborescence créée

web/tabler/
├── dist/css/          - Styles CSS Tabler officiels
├── dist/js/           - Scripts JavaScript Tabler
├── dist/libs/         - Bibliothèques tierces (ApexCharts, etc.)
├── dist/fonts/        - Polices (Inter)
├── icons/             - Pack complet Tabler Icons (~4700 SVG)
├── examples/          - Pages HTML d'exemple Tabler
└── app_bridge.js      - Placeholder QWebChannel (futur)

## Caractéristiques

- **100% Offline** : Aucun CDN, tous les assets sont locaux
- **Version officielle** : Pack Tabler original non modifié
- **Liens corrigés** : Toutes les références CDN remplacées par chemins locaux
- **Non-intrusif** : L'UI PyQt6 existante est intacte

## Smoke Test

### Lancer la démo Tabler
1. Démarrer l'application: `python payroll_app_qt_Version4.py`
2. Menu: **Développement** → **UI Tabler (Demo Offline)**
3. Explorer les exemples via la toolbar

### Pages disponibles
- Dashboard (page principale)
- Cards (composants cartes)
- Charts (graphiques)
- Tables (tableaux de données)
- Et toutes les autres pages d'exemple

## Utilisation des icônes

Toutes les icônes Tabler (~4700) sont dans `web/tabler/icons/`:
- Format SVG haute qualité
- Utilisables dans PyQt6 via QIcon/QPixmap
- Exemple: `web/tabler/icons/currency-dollar.svg`

## Prochaines étapes (non incluses)

1. Intégration QWebChannel pour communication Python ↔ JS
2. Remplacement progressif des composants PyQt6 par vues web Tabler
3. Connexion des exemples à la base de données PostgreSQL

## Maintenance

- Mise à jour Tabler: Télécharger nouvelle version et remplacer `web/tabler/dist/`
- Correction liens: Réexécuter `python tools/fix_tabler_links.py`
```

### Créer `.gitignore` pour web/

```
# Fichiers volumineux Tabler (optionnel: commiter ou non)
# web/tabler/dist/libs/
# web/tabler/icons/
```

## 6. Vérifications

### Checklist avant validation

- [ ] Dossier `web/tabler/` créé avec tous les sous-dossiers
- [ ] CSS Tabler présent: `web/tabler/dist/css/tabler.min.css`
- [ ] JS Tabler présent: `web/tabler/dist/js/tabler.min.js`
- [ ] Icônes présentes: `web/tabler/icons/*.svg` (~4700 fichiers)
- [ ] Exemples présents: `web/tabler/examples/*.html`
- [ ] Liens CDN corrigés dans tous les HTML
- [ ] Script `tools/fix_tabler_links.py` créé et exécuté
- [ ] `ui/tabler_viewer.py` créé
- [ ] Menu "Développement" ajouté dans `payroll_app_qt_Version4.py`
- [ ] `MIGRATION_TABLER_GUIDE.md` créé
- [ ] Application existante fonctionne sans changement
- [ ] Smoke test: Dashboard Tabler s'ouvre en local sans Internet

### Test offline complet

1. Désactiver la connexion Internet
2. Lancer l'application
3. Ouvrir "Développement" → "UI Tabler (Demo Offline)"
4. Naviguer entre Dashboard, Cards, Charts, Tables
5. Vérifier que tout s'affiche correctement (CSS, JS, icônes)

## Fichiers créés/modifiés

### Nouveaux fichiers

- `web/tabler/dist/css/*` (2 fichiers CSS + maps)
- `web/tabler/dist/js/*` (2+ fichiers JS + maps)
- `web/tabler/dist/libs/*` (multiples bibliothèques)
- `web/tabler/dist/fonts/*` (polices)
- `web/tabler/icons/*` (~4700 fichiers SVG)
- `web/tabler/examples/*` (10-20 fichiers HTML)
- `web/tabler/app_bridge.js`
- `tools/fix_tabler_links.py`
- `ui/tabler_viewer.py`
- `MIGRATION_TABLER_GUIDE.md`

### Fichiers modifiés

- `payroll_app_qt_Version4.py` (ajout menu Développement)
- `web/tabler/examples/*.html` (liens CDN → local)

### Aucun fichier supprimé

L'UI PyQt6 existante reste intacte.

## Notes importantes

- **Taille**: Le pack complet fait ~50-100 MB (libs + icônes)
- **Performance**: QWebEngineView nécessite PyQt6-WebEngine installé
- **Séparation**: L'UI Tabler et l'UI PyQt6 coexistent sans interférence
- **Migration progressive**: Les exemples Tabler servent de référence visuelle pour une future migration complète

### To-dos

- [ ] Supprimer/vider anciens composants KPI (kpi_card.py, kpi_board.py, dashboard_grid.py)
- [ ] Créer structure ui/tabler_components/ avec card.py et kpi.py
- [ ] Créer ui/themes/style_tabler_dark.qss avec palette Tabler
- [ ] Créer ui/themes/style_tabler_light.qss avec palette Tabler
- [ ] Ajouter thèmes Tabler dans config/theme_manager.py
- [ ] Télécharger 8+ icônes SVG Tabler et créer structure assets/icons/tabler/
- [ ] Remplacer KPI/grid dans ui/homepage.py avec composants Tabler placeholders
- [ ] Modifier payroll_app_qt_Version4.py pour menu thèmes et default Tabler Dark
- [ ] Créer MIGRATION_TABLER_GUIDE.md avec guide connexion DB future
- [ ] Tests visuels: lancer app, basculer thèmes, vérifier tous les composants