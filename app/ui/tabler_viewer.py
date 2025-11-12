#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tabler Viewer - Afficheur du dashboard Tabler (index.html par défaut)
RÈGLE: Source de vérité = index.html (dashboard unique Tabler pur)
Affichage offline complet sans CDN
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QStatusBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, QObject, pyqtSlot
from PyQt6.QtGui import QAction
import json
from pathlib import Path


class TablerViewer(QWidget):
    """
    Viewer pour afficher le dashboard Tabler (index.html)

    RÈGLES IMPORTANTES:
    - index.html est la SOURCE DE VÉRITÉ pour le dashboard
    - Toute carte/chart non visible sur index.html est OBSOLÈTE
    - Aucun CSS/JS custom qui imite Tabler
    - Tout fonctionne offline (assets locaux uniquement)
    """

    def __init__(self, parent=None, bridge=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard - Système de Contrôle de la Paie")
        self.resize(1400, 900)

        # Bridge Python ↔ JavaScript (si fourni par parent)
        self.bridge = bridge

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar pour navigation rapide
        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        layout.addWidget(toolbar)

        # Actions navigation pages principales
        self.add_page_action(toolbar, "🏠 Dashboard", "index.html")
        self.add_page_action(toolbar, "📊 Base de données", "database.html")
        self.add_page_action(toolbar, "👤 Employés", "employees.html")
        self.add_page_action(toolbar, "📅 Périodes", "periods.html")
        self.add_page_action(toolbar, "📥 Import", "import.html")
        self.add_page_action(toolbar, "🤖 Assistant IA", "assistant.html")

        toolbar.addSeparator()

        # Action reload
        reload_action = QAction("🔄 Actualiser", self)
        reload_action.setStatusTip("Recharger la page actuelle")
        reload_action.setShortcut("F5")
        reload_action.triggered.connect(self.reload_page)
        toolbar.addAction(reload_action)

        toolbar.addSeparator()

        # Actions navigation
        back_action = QAction("⬅ Retour", self)
        back_action.setStatusTip("Page précédente")
        back_action.setShortcut("Alt+Left")
        back_action.triggered.connect(self.go_back)
        toolbar.addAction(back_action)

        forward_action = QAction("➡ Suivant", self)
        forward_action.setStatusTip("Page suivante")
        forward_action.setShortcut("Alt+Right")
        forward_action.triggered.connect(self.go_forward)
        toolbar.addAction(forward_action)

        # WebEngineView
        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.on_load_finished)
        layout.addWidget(self.web_view)

        # Configurer WebChannel si bridge fourni
        if self.bridge:
            self.channel = QWebChannel()
            self.channel.registerObject("AppBridge", self.bridge)
            self.web_view.page().setWebChannel(self.channel)
            print("✓ WebChannel enregistré dans Tabler Viewer")

        # Barre de statut
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Prêt")

        # Charger le dashboard par défaut (SOURCE DE VÉRITÉ)
        self.load_page("index.html")

    def add_page_action(self, toolbar, label, filename):
        """Ajoute une action pour charger une page"""
        action = QAction(label, self)
        action.setStatusTip(f"Ouvrir {filename}")
        action.triggered.connect(lambda: self.load_page(filename))
        toolbar.addAction(action)

    def load_page(self, filename):
        """
        Charge une page HTML depuis web/tabler/

        RÈGLE: index.html est la page par défaut (dashboard unique)
        """
        # Construire le chemin vers le fichier HTML
        base_path = Path(__file__).parent.parent
        html_path = base_path / "web" / "tabler" / filename
        html_path = html_path.resolve()

        if html_path.exists():
            url = QUrl.fromLocalFile(str(html_path))
            self.web_view.setUrl(url)
            self.status_bar.showMessage(f"Chargement: {filename}...")
            print(f"✅ Chargement Tabler: {html_path}")
        else:
            self.status_bar.showMessage(f"❌ Fichier introuvable: {filename}", 5000)
            print(f"❌ Fichier introuvable: {html_path}")

            # Afficher message d'erreur dans le viewer
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Erreur</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f1f5f9;
                    }}
                    .error-box {{
                        background: white;
                        padding: 2rem;
                        border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        max-width: 600px;
                    }}
                    h1 {{ color: #dc2626; }}
                    code {{ background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1>❌ Fichier introuvable</h1>
                    <p><strong>Fichier demandé :</strong></p>
                    <code>{filename}</code>
                    <p><strong>Chemin attendu :</strong></p>
                    <code>{html_path}</code>
                    <p>Vérifiez que les fichiers Tabler sont bien présents dans <code>web/tabler/</code>.</p>
                    <p><a href="#" onclick="window.location.reload()">🔄 Réessayer</a></p>
                </div>
            </body>
            </html>
            """
            self.web_view.setHtml(error_html)

    def reload_page(self):
        """Recharge la page actuelle"""
        self.web_view.reload()
        self.status_bar.showMessage("Rechargement...", 2000)

    def go_back(self):
        """Page précédente"""
        if self.web_view.history().canGoBack():
            self.web_view.back()

    def go_forward(self):
        """Page suivante"""
        if self.web_view.history().canGoForward():
            self.web_view.forward()

    def on_load_finished(self, ok):
        """Callback quand le chargement est terminé"""
        if ok:
            title = self.web_view.title()
            url = self.web_view.url().toString()
            self.status_bar.showMessage(f"✅ Page chargée: {title}", 3000)
            print(f"✅ Tabler page loaded: {title}")
        else:
            self.status_bar.showMessage("❌ Erreur de chargement", 5000)
            print("❌ Erreur chargement page Tabler")


def main():
    """Test standalone du viewer"""
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Créer un bridge de test (placeholder)
    class TestBridge(QObject):
        @pyqtSlot(result=str)
        def ping(self):
            return json.dumps({"status": "ok", "message": "Test bridge actif"})

        @pyqtSlot(str, result=str)
        def get_kpis(self, period=""):
            return json.dumps(
                {
                    "masse_salariale": 125000.50,
                    "nb_employes": 45,
                    "deductions": -25000.00,
                    "net_moyen": 2777.78,
                    "period": period or "2024-03",
                }
            )

    bridge = TestBridge()
    viewer = TablerViewer(bridge=bridge)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
