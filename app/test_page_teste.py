"""
Test de la page teste.html
Lance l'application et ouvre directement la page de test DataTable
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from payroll_app_qt_Version4 import MainWindow


def main():
    print("=" * 60)
    print("TEST PAGE TESTE - DataTable natif")
    print("=" * 60)

    app = QApplication(sys.argv)
    win = MainWindow()

    def load_teste_page():
        if hasattr(win, "tabler_viewer") and win.tabler_viewer:
            win.tabler_viewer.load_page("teste.html")
            print("\nOK: Page teste.html chargee")
            print("\n→ Verifiez que le tableau affiche:")
            print("   - Nom")
            print("   - Categorie d'emploi")
            print("   - Titre d'emploi")
            print("   - Salaire net")
            print("\n→ 295 employes devraient etre affiches")
            print("→ Total: 538,402.22 $")
            print("\n→ Fermez l'application pour terminer\n")
        else:
            print("FAIL: Erreur: Viewer Tabler non trouve")

    QTimer.singleShot(500, load_teste_page)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
