"""
Test correct de la page employés avec l'AppBridge
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Importer la fenêtre principale qui contient AppBridge
from payroll_app_qt_Version4 import MainWindow


def main():
    print("=" * 60)
    print("TEST PAGE EMPLOYÉS - avec AppBridge correct")
    print("=" * 60)

    # Créer l'application Qt
    app = QApplication(sys.argv)

    # Créer la fenêtre principale
    win = MainWindow()

    # Après un court délai, charger la page employés
    def load_employees_page():
        if hasattr(win, "tabler_viewer") and win.tabler_viewer:
            win.tabler_viewer.load_page("employees.html")
            print("OK: Page employés chargée")
            print("\n→ Vérifiez que la liste des employés s'affiche dans le tableau")
            print(
                "→ Si le tableau est vide, ouvrez la console développeur pour voir les logs"
            )
            print("→ Fermez l'application pour terminer\n")
        else:
            print("FAIL: Erreur: Viewer Tabler non trouvé")

    # Charger la page après l'initialisation de l'UI (500ms)
    QTimer.singleShot(500, load_employees_page)

    # Afficher la fenêtre
    win.show()

    # Lancer l'app
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
